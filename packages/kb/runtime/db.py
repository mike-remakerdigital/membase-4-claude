"""
Membase Knowledge Database - append-only SQLite store for project artifacts.

No UPDATE in place and no DELETE on versioned artifacts. Every mutation creates a
new versioned record. Claude or Codex is the sole writer; the owner observes via
the read-only UI.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).parent / "knowledge.db"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS specifications (
    rowid INTEGER PRIMARY KEY AUTOINCREMENT,
    id TEXT NOT NULL,
    version INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    type TEXT DEFAULT 'requirement',
    status TEXT NOT NULL,
    tags TEXT,
    assertions TEXT,
    changed_by TEXT NOT NULL,
    changed_at TEXT NOT NULL,
    change_reason TEXT NOT NULL,
    UNIQUE(id, version)
);

CREATE TABLE IF NOT EXISTS operational_procedures (
    rowid INTEGER PRIMARY KEY AUTOINCREMENT,
    id TEXT NOT NULL,
    version INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    type TEXT,
    trigger TEXT,
    scope TEXT,
    steps TEXT,
    changed_by TEXT NOT NULL,
    changed_at TEXT NOT NULL,
    change_reason TEXT NOT NULL,
    UNIQUE(id, version)
);

CREATE TABLE IF NOT EXISTS assertion_runs (
    rowid INTEGER PRIMARY KEY AUTOINCREMENT,
    spec_id TEXT NOT NULL,
    spec_version INTEGER NOT NULL,
    run_at TEXT NOT NULL,
    overall_passed INTEGER NOT NULL,
    results TEXT NOT NULL,
    triggered_by TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS session_prompts (
    rowid INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    event_type TEXT NOT NULL DEFAULT 'created',
    created_at TEXT NOT NULL,
    prompt_text TEXT NOT NULL,
    context TEXT
);

CREATE INDEX IF NOT EXISTS idx_specs_id_version ON specifications(id, version);
CREATE INDEX IF NOT EXISTS idx_specs_status ON specifications(status);
CREATE INDEX IF NOT EXISTS idx_specs_changed_at ON specifications(changed_at);
CREATE INDEX IF NOT EXISTS idx_op_procs_id_version ON operational_procedures(id, version);
CREATE INDEX IF NOT EXISTS idx_assertion_runs_spec ON assertion_runs(spec_id, rowid);
CREATE INDEX IF NOT EXISTS idx_session_prompts_session ON session_prompts(session_id, rowid);

CREATE VIEW IF NOT EXISTS current_specifications AS
SELECT s.* FROM specifications s
INNER JOIN (SELECT id, MAX(version) AS max_v FROM specifications GROUP BY id) m
ON s.id = m.id AND s.version = m.max_v;

CREATE VIEW IF NOT EXISTS current_operational_procedures AS
SELECT o.* FROM operational_procedures o
INNER JOIN (SELECT id, MAX(version) AS max_v FROM operational_procedures GROUP BY id) m
ON o.id = m.id AND o.version = m.max_v;
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    for key in ("assertions", "results", "steps", "tags", "context"):
        if key in data and data[key] and isinstance(data[key], str):
            try:
                parsed = json.loads(data[key])
                if isinstance(parsed, str):
                    try:
                        parsed = json.loads(parsed)
                    except (json.JSONDecodeError, TypeError):
                        pass
                data[f"_{key}_parsed"] = parsed
            except (json.JSONDecodeError, TypeError):
                pass
    return data


class KnowledgeDB:
    """Append-only knowledge database with a minimal reusable schema."""

    _UNSET = object()

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self._conn: sqlite3.Connection | None = None
        self._ensure_schema()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def _ensure_schema(self) -> None:
        conn = self._get_conn()
        conn.executescript(SCHEMA_SQL)
        conn.commit()

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def _next_spec_version(self, spec_id: str) -> int:
        row = self._get_conn().execute(
            "SELECT MAX(version) FROM specifications WHERE id = ?",
            (spec_id,),
        ).fetchone()
        return (row[0] or 0) + 1

    def insert_spec(
        self,
        id: str,
        title: str,
        status: str = "specified",
        changed_by: str = "claude",
        change_reason: str = "created",
        *,
        description: str | None = None,
        spec_type: str = "requirement",
        tags: list[str] | None = None,
        assertions: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        version = self._next_spec_version(id)
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO specifications
               (id, version, title, description, type, status, tags, assertions,
                changed_by, changed_at, change_reason)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                id,
                version,
                title,
                description,
                spec_type,
                status,
                json.dumps(tags) if tags else None,
                json.dumps(assertions) if assertions else None,
                changed_by,
                _now(),
                change_reason,
            ),
        )
        conn.commit()
        return self.get_spec(id)

    def update_spec(
        self,
        id: str,
        changed_by: str,
        change_reason: str,
        **fields: Any,
    ) -> dict[str, Any]:
        current = self.get_spec(id)
        if not current:
            raise ValueError(f"Spec {id} not found")

        version = self._next_spec_version(id)
        title = fields.get("title", current["title"])
        description = fields.get("description", current["description"])
        spec_type = fields.get("spec_type", current.get("type", "requirement"))
        status = fields.get("status", current["status"])

        raw_tags = fields.get("tags", self._UNSET)
        if raw_tags is not self._UNSET:
            tags_json = json.dumps(raw_tags) if raw_tags is not None else None
        else:
            tags_json = current["tags"]

        raw_assertions = fields.get("assertions", self._UNSET)
        if raw_assertions is not self._UNSET:
            assertions_json = json.dumps(raw_assertions) if raw_assertions is not None else None
        else:
            assertions_json = current["assertions"]

        conn = self._get_conn()
        conn.execute(
            """INSERT INTO specifications
               (id, version, title, description, type, status, tags, assertions,
                changed_by, changed_at, change_reason)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                id,
                version,
                title,
                description,
                spec_type,
                status,
                tags_json,
                assertions_json,
                changed_by,
                _now(),
                change_reason,
            ),
        )
        conn.commit()
        return self.get_spec(id)

    def get_spec(self, spec_id: str) -> dict[str, Any] | None:
        row = self._get_conn().execute(
            "SELECT * FROM current_specifications WHERE id = ?",
            (spec_id,),
        ).fetchone()
        return _row_to_dict(row) if row else None

    def get_spec_history(self, spec_id: str) -> list[dict[str, Any]]:
        rows = self._get_conn().execute(
            "SELECT * FROM specifications WHERE id = ? ORDER BY version DESC",
            (spec_id,),
        ).fetchall()
        return [_row_to_dict(row) for row in rows]

    def list_specs(
        self,
        *,
        status: str | None = None,
        search: str | None = None,
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM current_specifications WHERE 1=1"
        params: list[Any] = []
        if status:
            query += " AND status = ?"
            params.append(status)
        if search:
            query += " AND (title LIKE ? OR description LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        query += " ORDER BY id"
        rows = self._get_conn().execute(query, params).fetchall()
        return [_row_to_dict(row) for row in rows]

    def _next_op_version(self, proc_id: str) -> int:
        row = self._get_conn().execute(
            "SELECT MAX(version) FROM operational_procedures WHERE id = ?",
            (proc_id,),
        ).fetchone()
        return (row[0] or 0) + 1

    def insert_op_procedure(
        self,
        id: str,
        title: str,
        changed_by: str = "claude",
        change_reason: str = "created",
        *,
        description: str | None = None,
        type: str | None = None,
        trigger: str | None = None,
        scope: str | None = None,
        steps: list[str] | None = None,
    ) -> dict[str, Any]:
        version = self._next_op_version(id)
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO operational_procedures
               (id, version, title, description, type, trigger, scope, steps,
                changed_by, changed_at, change_reason)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                id,
                version,
                title,
                description,
                type,
                trigger,
                scope,
                json.dumps(steps) if steps else None,
                changed_by,
                _now(),
                change_reason,
            ),
        )
        conn.commit()
        return self.get_op_procedure(id)

    def get_op_procedure(self, proc_id: str) -> dict[str, Any] | None:
        row = self._get_conn().execute(
            "SELECT * FROM current_operational_procedures WHERE id = ?",
            (proc_id,),
        ).fetchone()
        return _row_to_dict(row) if row else None

    def list_op_procedures(self) -> list[dict[str, Any]]:
        rows = self._get_conn().execute(
            "SELECT * FROM current_operational_procedures ORDER BY id"
        ).fetchall()
        return [_row_to_dict(row) for row in rows]

    def insert_assertion_run(
        self,
        spec_id: str,
        spec_version: int,
        overall_passed: bool,
        results: list[dict[str, Any]],
        triggered_by: str,
    ) -> None:
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO assertion_runs
               (spec_id, spec_version, run_at, overall_passed, results, triggered_by)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                spec_id,
                spec_version,
                _now(),
                int(overall_passed),
                json.dumps(results),
                triggered_by,
            ),
        )
        conn.commit()

    def get_latest_assertion_run(self, spec_id: str) -> dict[str, Any] | None:
        row = self._get_conn().execute(
            "SELECT * FROM assertion_runs WHERE spec_id = ? ORDER BY rowid DESC LIMIT 1",
            (spec_id,),
        ).fetchone()
        return _row_to_dict(row) if row else None

    def get_all_latest_assertion_runs(self) -> list[dict[str, Any]]:
        rows = self._get_conn().execute(
            """SELECT a.* FROM assertion_runs a
               INNER JOIN (
                   SELECT spec_id, MAX(rowid) AS max_rowid
                   FROM assertion_runs GROUP BY spec_id
               ) m ON a.spec_id = m.spec_id AND a.rowid = m.max_rowid
               ORDER BY a.spec_id"""
        ).fetchall()
        return [_row_to_dict(row) for row in rows]

    def _next_session_prompt_version(self, session_id: str) -> int:
        row = self._get_conn().execute(
            "SELECT MAX(version) FROM session_prompts WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        return (row[0] or 0) + 1

    def insert_session_prompt(
        self,
        session_id: str,
        prompt_text: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        version = self._next_session_prompt_version(session_id)
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO session_prompts
               (session_id, version, event_type, created_at, prompt_text, context)
               VALUES (?, ?, 'created', ?, ?, ?)""",
            (
                session_id,
                version,
                _now(),
                prompt_text,
                json.dumps(context) if context else None,
            ),
        )
        conn.commit()
        return self._get_session_prompt(session_id)

    def _get_session_prompt(self, session_id: str) -> dict[str, Any] | None:
        row = self._get_conn().execute(
            "SELECT * FROM session_prompts WHERE session_id = ? ORDER BY rowid DESC LIMIT 1",
            (session_id,),
        ).fetchone()
        return _row_to_dict(row) if row else None

    def get_next_session_prompt(self) -> dict[str, Any] | None:
        row = self._get_conn().execute(
            """SELECT p.* FROM session_prompts p
               INNER JOIN (
                   SELECT session_id, MAX(rowid) AS max_rowid
                   FROM session_prompts GROUP BY session_id
               ) m ON p.session_id = m.session_id AND p.rowid = m.max_rowid
               WHERE p.event_type = 'created'
               ORDER BY p.rowid DESC LIMIT 1"""
        ).fetchone()
        return _row_to_dict(row) if row else None

    def consume_session_prompt(self, session_id: str) -> None:
        current = self._get_session_prompt(session_id)
        if not current:
            return
        version = self._next_session_prompt_version(session_id)
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO session_prompts
               (session_id, version, event_type, created_at, prompt_text, context)
               VALUES (?, ?, 'consumed', ?, ?, ?)""",
            (
                session_id,
                version,
                _now(),
                current.get("prompt_text", ""),
                current.get("context"),
            ),
        )
        conn.commit()

    def get_summary(self) -> dict[str, Any]:
        conn = self._get_conn()

        specs = conn.execute(
            "SELECT status, COUNT(*) AS cnt FROM current_specifications GROUP BY status"
        ).fetchall()
        spec_counts = {row["status"]: row["cnt"] for row in specs}

        op_count = conn.execute(
            "SELECT COUNT(*) FROM current_operational_procedures"
        ).fetchone()[0]

        assertion_stats = conn.execute(
            """SELECT COUNT(*) AS total, SUM(overall_passed) AS passed
               FROM (
                 SELECT a.* FROM assertion_runs a
                 INNER JOIN (
                   SELECT spec_id, MAX(rowid) AS max_rowid
                   FROM assertion_runs GROUP BY spec_id
                 ) m ON a.spec_id = m.spec_id AND a.rowid = m.max_rowid
               )"""
        ).fetchone()

        total_versions = conn.execute(
            "SELECT COUNT(*) FROM specifications"
        ).fetchone()[0]

        pending_prompts = conn.execute(
            """SELECT COUNT(*) FROM (
                   SELECT p.event_type
                   FROM session_prompts p
                   INNER JOIN (
                       SELECT session_id, MAX(rowid) AS max_rowid
                       FROM session_prompts GROUP BY session_id
                   ) m ON p.session_id = m.session_id AND p.rowid = m.max_rowid
                   WHERE p.event_type = 'created'
               )"""
        ).fetchone()[0]

        total_assertions = assertion_stats["total"] or 0
        passed_assertions = assertion_stats["passed"] or 0

        return {
            "spec_counts": spec_counts,
            "spec_total": sum(spec_counts.values()),
            "spec_verified": spec_counts.get("verified", 0),
            "spec_implemented": spec_counts.get("implemented", 0),
            "spec_specified": spec_counts.get("specified", 0),
            "spec_retired": spec_counts.get("retired", 0),
            "spec_total_versions": total_versions,
            "op_procedure_total": op_count,
            "assertions_total": total_assertions,
            "assertions_passed": passed_assertions,
            "assertions_failed": total_assertions - passed_assertions,
            "session_prompt_pending": pending_prompts,
        }

    def get_history(self, *, limit: int = 50) -> list[dict[str, Any]]:
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT 'specifications' AS table_name, id AS record_id,
                      version, title, changed_by, changed_at, change_reason
               FROM specifications
               UNION ALL
               SELECT 'operational_procedures', id, version, title,
                      changed_by, changed_at, change_reason
               FROM operational_procedures
               ORDER BY changed_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]

    def export_json(self, output_path: str | Path | None = None) -> str:
        conn = self._get_conn()
        tables = [
            "specifications",
            "operational_procedures",
            "assertion_runs",
            "session_prompts",
        ]
        export = {"exported_at": _now(), "tables": {}}
        for table in tables:
            rows = conn.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
            export["tables"][table] = [_row_to_dict(row) for row in rows]

        if output_path is None:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            output_path = self.db_path.parent / f"knowledge-export-{timestamp}.json"
        else:
            output_path = Path(output_path)

        output_path.write_text(json.dumps(export, indent=2, default=str), encoding="utf-8")
        return str(output_path)
