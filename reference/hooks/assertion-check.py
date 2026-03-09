#!/usr/bin/env python3
"""
Membase Reference — SessionStart Hook

Runs at the start of every Claude Code session. Three responsibilities:

1. Run feature assertions and return a summary (regression guard).
   Classifies failures as regressions (implemented/verified specs now
   failing) vs expected (specified — not yet implemented).

2. Prune old assertion_runs to keep DB size manageable.
   NOTE: This is NOT a contradiction with append-only versioning.
   Versioned artifacts (specs, procedures) are NEVER deleted.
   Assertion runs are telemetry — keeping only the latest 5 per spec
   preserves trend data while preventing unbounded table growth.

3. Read the latest unconsumed session handoff prompt and inject it
   as context so the new session knows where the previous one left off.

Stdin:  JSON (SessionStart payload from Claude Code)
Stdout: JSON {"additionalContext": "..."} or {}
Exit:   Always 0

MIT License — see LICENSE for details.
"""

import json
import sys
import os
from pathlib import Path

# Resolve project directory from CLAUDE_PROJECT_DIR or cwd
PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()))
# Adjust this path to wherever your knowledge-db module lives
KB_DIR = PROJECT_DIR / "reference"


def _run_assertions(db) -> list[str]:
    """Run assertions and return context lines.

    Differentiates between expected failures (specified — not yet implemented)
    and regressions (implemented/verified — should be passing).
    """
    try:
        from assertions import run_all_assertions

        summary = run_all_assertions(db, triggered_by="session-start")
        passed = summary.get("passed", 0)
        failed = summary.get("failed", 0)
        total = summary.get("specs_with_assertions", 0)

        lines = [f"Assertion check: {passed}/{total} PASS, {failed} FAIL"]

        failures = [
            d for d in summary.get("details", [])
            if not d.get("skipped") and not d["overall_passed"]
        ]
        if failures:
            regressions = []
            expected = []
            for f in failures:
                spec = db.get_spec(f["spec_id"])
                status = spec["status"] if spec else "unknown"
                if status in ("implemented", "verified"):
                    regressions.append((f, status))
                else:
                    expected.append((f, status))

            if regressions:
                lines.append("REGRESSIONS (implemented/verified specs now failing):")
                for f, status in regressions:
                    lines.append(f"  [{f['spec_id']}] ({status}) {f['title']}")
                lines.append("  ^^^ These require investigation before proceeding.")

            if expected:
                lines.append("Expected failures (specified -- not yet implemented):")
                for f, status in expected:
                    lines.append(f"  [{f['spec_id']}] ({status}) {f['title']}")

        return lines
    except Exception as e:
        return [f"Assertion check error: {e}"]


def _prune_assertion_runs(db) -> list[str]:
    """Prune old assertion_runs to keep DB size manageable.

    WHY THIS ISN'T A CONTRADICTION WITH "NEVER DELETE":
    Membase's append-only discipline applies to versioned artifacts —
    specifications, operational procedures, and other decision records.
    These represent the project's institutional memory and MUST NOT be
    deleted, even when superseded (they become historical versions).

    Assertion runs, however, are telemetry — automated check results
    generated every session. Without pruning, this table grows without
    bound (e.g., ~230K rows, ~30MB after 120 sessions). Keeping the
    latest 5 runs per spec preserves enough history for trend analysis
    while reducing storage ~97%.
    """
    try:
        pruned = db.prune_assertion_runs(keep=5)
        if pruned > 0:
            return [f"Assertion runs pruned: {pruned} old runs removed"]
        return []
    except Exception as e:
        return [f"Assertion pruning error: {e}"]


def _read_handoff_prompt(db) -> list[str]:
    """Read and consume the latest session handoff prompt."""
    try:
        prompt = db.get_next_session_prompt()
        if not prompt:
            return []

        session_id = prompt["session_id"]
        prompt_text = prompt["prompt_text"]

        # Parse context
        context_data = prompt.get("_context_parsed") or {}
        if not context_data and prompt.get("context"):
            try:
                context_data = json.loads(prompt["context"])
            except (ValueError, TypeError):
                context_data = {}

        lines = [
            "",
            "=" * 50,
            f"  SESSION HANDOFF from {session_id}",
            "=" * 50,
        ]

        if context_data:
            if context_data.get("production_version"):
                lines.append(f"  Version: v{context_data['production_version']}")
            if context_data.get("test_count") is not None:
                tc = context_data["test_count"]
                tf = context_data.get("test_failures", 0)
                lines.append(f"  Tests: {tc} passed, {tf} failed")
            if context_data.get("next_tasks"):
                lines.append("  Next tasks:")
                for task in context_data["next_tasks"]:
                    lines.append(f"    - {task}")

        lines.append("-" * 50)
        lines.append(prompt_text)
        lines.append("=" * 50)

        db.consume_session_prompt(session_id)
        return lines
    except Exception as e:
        return [f"Session handoff read error: {e}"]


def main():
    # Consume stdin (required by hook protocol)
    try:
        json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        pass

    # Check if knowledge database exists
    db_path = KB_DIR / "knowledge.db"
    if not db_path.exists():
        json.dump({}, sys.stdout)
        sys.exit(0)

    # Import and run
    sys.path.insert(0, str(KB_DIR))
    try:
        from db import KnowledgeDB

        db = KnowledgeDB(str(db_path))
        try:
            lines = _run_assertions(db)
            lines.extend(_prune_assertion_runs(db))
            lines.extend(_read_handoff_prompt(db))
        finally:
            db.close()

        context = "\n".join(lines)
        json.dump({"additionalContext": context}, sys.stdout)

    except Exception as e:
        json.dump({"additionalContext": f"SessionStart hook error: {e}"}, sys.stdout)

    sys.exit(0)


if __name__ == "__main__":
    main()
