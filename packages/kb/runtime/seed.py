"""
Membase starter seed data for a new project knowledge base.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

try:
    from .db import KnowledgeDB
except ImportError:  # pragma: no cover - used by copied project runtime
    from db import KnowledgeDB

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "knowledge.db"


def _seed_specs(db: KnowledgeDB) -> None:
    db.insert_spec(
        id="SPEC-001",
        title="Append-only versioned storage",
        description=(
            "The knowledge database must use append-only versioning with "
            "UNIQUE(id, version) constraints and insert-only mutation flows."
        ),
        status="verified",
        assertions=[
            {
                "type": "grep",
                "pattern": "UNIQUE\\(id,\\s*version\\)",
                "file": "tools/knowledge-db/db.py",
                "description": "Schema enforces UNIQUE(id, version)",
            },
            {
                "type": "grep",
                "pattern": "INSERT INTO",
                "file": "tools/knowledge-db/db.py",
                "min_count": 3,
                "description": "Runtime uses insert-only mutations",
            },
        ],
    )

    db.insert_spec(
        id="SPEC-002",
        title="Machine-verifiable assertions",
        description=(
            "The assertion runner must support grep, glob, and grep_absent "
            "checks against the managed project workspace."
        ),
        status="verified",
        assertions=[
            {
                "type": "grep",
                "pattern": "grep|glob|grep_absent",
                "file": "tools/knowledge-db/assertions.py",
                "min_count": 5,
                "description": "All assertion types are referenced in runtime code",
            },
            {
                "type": "grep",
                "pattern": "def run_single_assertion",
                "file": "tools/knowledge-db/assertions.py",
                "description": "Single-assertion runner exists",
            },
        ],
    )

    db.insert_spec(
        id="SPEC-003",
        title="Session handoff prompts",
        description=(
            "The database must support session-to-session context transfer "
            "through insert, get, and consume prompt lifecycle methods."
        ),
        status="implemented",
        assertions=[
            {
                "type": "grep",
                "pattern": "def insert_session_prompt",
                "file": "tools/knowledge-db/db.py",
                "description": "insert_session_prompt method exists",
            },
            {
                "type": "grep",
                "pattern": "def get_next_session_prompt",
                "file": "tools/knowledge-db/db.py",
                "description": "get_next_session_prompt method exists",
            },
            {
                "type": "grep",
                "pattern": "def consume_session_prompt",
                "file": "tools/knowledge-db/db.py",
                "description": "consume_session_prompt method exists",
            },
        ],
    )

    db.insert_spec(
        id="SPEC-004",
        title="Read-only KB dashboard",
        description=(
            "The managed KB runtime must expose a read-only dashboard for "
            "observing specs, assertions, procedures, and history."
        ),
        status="implemented",
        assertions=[
            {
                "type": "glob",
                "pattern": "tools/knowledge-db/app.py",
                "description": "Dashboard entrypoint exists",
            },
            {
                "type": "glob",
                "pattern": "tools/knowledge-db/templates/*.html",
                "description": "Dashboard templates exist",
            },
            {
                "type": "glob",
                "pattern": "tools/knowledge-db/static/*.css",
                "description": "Dashboard static assets exist",
            },
        ],
    )

    db.insert_spec(
        id="SPEC-005",
        title="Session-start hook integration",
        description=(
            "Future Membase hook extraction should trigger KB verification at "
            "session start and classify failures as regressions versus expected gaps."
        ),
        status="specified",
        assertions=[],
    )

    db.insert_spec(
        id="SPEC-006",
        title="KB-aware workflow automation",
        description=(
            "Future Membase skills and hooks should write project knowledge into "
            "the KB instead of drifting markdown backlog files."
        ),
        status="specified",
        assertions=[],
    )

    db.insert_spec(
        id="SPEC-007",
        title="Legacy XML export format",
        description=(
            "The KB used to support XML export for tooling integration. JSON export "
            "supersedes that format and remains the supported path."
        ),
        status="retired",
        assertions=[],
    )


def _seed_operational_procedures(db: KnowledgeDB) -> None:
    db.insert_op_procedure(
        id="PROC-001",
        title="Session Wrap-Up",
        description="Standard procedure for ending a work session.",
        trigger="End of every work session",
        scope="session",
        steps=[
            "Update KB artifacts to reflect changes made during the session.",
            "Run membase kb verify to confirm no regressions were introduced.",
            "Update memory or handoff notes for the next session.",
            "Store a next-session prompt through the KB runtime.",
        ],
    )

    db.insert_op_procedure(
        id="PROC-002",
        title="Adding a New Feature",
        description="Workflow for implementing a new capability in a Membase project.",
        trigger="New feature request from the owner",
        scope="feature",
        steps=[
            "Create or update KB specifications describing the requirement.",
            "Add machine-verifiable assertions where practical.",
            "Implement the feature in the codebase.",
            "Run membase kb verify and relevant tests.",
            "Promote spec status from specified to implemented to verified as evidence accumulates.",
        ],
    )


def _seed_session_prompt(db: KnowledgeDB) -> None:
    db.insert_session_prompt(
        session_id="S001",
        prompt_text=(
            "Continue the project from the seeded Membase platform state.\n"
            "1. Run membase kb verify to confirm starter assertions pass.\n"
            "2. Open the KB dashboard with membase kb serve.\n"
            "3. Add project-specific specifications and tests."
        ),
        context={
            "platform_version": "0.1.0",
            "next_tasks": [
                "Run KB verification",
                "Review the local dashboard",
                "Start project-specific specs",
            ],
        },
    )


def seed(
    *,
    db_path: str | Path | None = None,
    force: bool = False,
) -> dict[str, Any]:
    db = KnowledgeDB(db_path or DEFAULT_DB_PATH)
    try:
        existing = db.get_summary()
        if existing["spec_total"] and not force:
            raise RuntimeError(
                f"KB already contains {existing['spec_total']} current spec(s). "
                "Refusing to re-seed without --force."
            )

        _seed_specs(db)
        _seed_operational_procedures(db)
        _seed_session_prompt(db)
        return db.get_summary()
    finally:
        db.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seed a Membase project knowledge base")
    parser.add_argument("--db", default=None, help="Explicit KB database path")
    parser.add_argument("--force", action="store_true", help="Allow re-seeding an existing KB")
    args = parser.parse_args(argv)

    db_path = Path(args.db).resolve() if args.db else DEFAULT_DB_PATH.resolve()
    try:
        summary = seed(db_path=db_path, force=args.force)
    except RuntimeError as exc:
        print(str(exc))
        return 1

    print(f"Seeded knowledge database at: {db_path}")
    print(f"  Specs:        {summary['spec_total']}")
    print(f"  Procedures:   {summary['op_procedure_total']}")
    print(f"  Prompts:      {summary['session_prompt_pending']}")
    print("")
    print("Run verification: membase kb verify")
    print("Start web UI:     membase kb serve")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
