"""
Membase Reference — Example Seed Data

Creates a knowledge database populated with self-referential specs,
operational procedures, and a session prompt. The assertions check
the reference/ files themselves, so running assertions.py immediately
after seeding gives real PASS/FAIL feedback.

Usage:
  python reference/seed.py              # creates reference/knowledge.db
  python reference/assertions.py        # run assertions against seed data

MIT License — see LICENSE for details.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Import sibling module
sys.path.insert(0, str(Path(__file__).parent))
from db import KnowledgeDB


def seed(db_path: str | None = None) -> None:
    """Populate a knowledge database with example data."""
    db = KnowledgeDB(db_path)

    try:
        # ── Specs: 2 verified, 2 implemented, 2 specified, 1 retired ──

        db.insert_spec(
            id="SPEC-001",
            title="Append-only versioned storage",
            description=(
                "The knowledge database must use append-only versioning with "
                "UNIQUE(id, version) constraints. No UPDATE or DELETE on "
                "versioned tables. [Source: reference/db.py]"
            ),
            status="verified",
            assertions=[
                {
                    "type": "grep",
                    "pattern": "UNIQUE\\(id,\\s*version\\)",
                    "file": "reference/db.py",
                    "description": "Schema enforces UNIQUE(id, version)",
                },
                {
                    "type": "grep",
                    "pattern": "INSERT INTO",
                    "file": "reference/db.py",
                    "min_count": 3,
                    "description": "Multiple INSERT statements exist",
                },
            ],
        )

        db.insert_spec(
            id="SPEC-002",
            title="Machine-verifiable assertions",
            description=(
                "The assertion runner must support three types: grep, glob, "
                "and grep_absent. Each returns a clear PASS/FAIL result. "
                "[Source: reference/assertions.py]"
            ),
            status="verified",
            assertions=[
                {
                    "type": "grep",
                    "pattern": "grep|glob|grep_absent",
                    "file": "reference/assertions.py",
                    "min_count": 5,
                    "description": "All three assertion types referenced",
                },
                {
                    "type": "grep",
                    "pattern": "def run_single_assertion",
                    "file": "reference/assertions.py",
                    "description": "Core assertion function exists",
                },
            ],
        )

        db.insert_spec(
            id="SPEC-003",
            title="Session handoff prompts",
            description=(
                "The database must support session-to-session context transfer "
                "via insert/get/consume prompt lifecycle. "
                "[Source: reference/db.py]"
            ),
            status="implemented",
            assertions=[
                {
                    "type": "grep",
                    "pattern": "def insert_session_prompt",
                    "file": "reference/db.py",
                    "description": "insert_session_prompt method exists",
                },
                {
                    "type": "grep",
                    "pattern": "def get_next_session_prompt",
                    "file": "reference/db.py",
                    "description": "get_next_session_prompt method exists",
                },
                {
                    "type": "grep",
                    "pattern": "def consume_session_prompt",
                    "file": "reference/db.py",
                    "description": "consume_session_prompt method exists",
                },
            ],
        )

        db.insert_spec(
            id="SPEC-004",
            title="Read-only web dashboard",
            description=(
                "A Flask web UI provides read-only access to specs, assertions, "
                "and operational procedures. [Source: reference/app.py]"
            ),
            status="implemented",
            assertions=[
                {
                    "type": "glob",
                    "pattern": "reference/app.py",
                    "description": "Flask app file exists",
                },
                {
                    "type": "glob",
                    "pattern": "reference/templates/*.html",
                    "description": "HTML templates exist",
                },
            ],
        )

        db.insert_spec(
            id="SPEC-005",
            title="SessionStart hook with regression detection",
            description=(
                "A Claude Code SessionStart hook runs assertions at session "
                "start and classifies failures as regressions (implemented/"
                "verified specs failing) vs expected (specified — not yet "
                "implemented)."
            ),
            status="specified",
            assertions=[
                {
                    "type": "glob",
                    "pattern": "reference/hooks/assertion-check.py",
                    "description": "SessionStart hook file exists",
                },
            ],
        )

        db.insert_spec(
            id="SPEC-006",
            title="Spec language classification hook",
            description=(
                "A UserPromptSubmit hook detects specification language in "
                "user prompts and reminds the AI to follow spec-first workflow."
            ),
            status="specified",
            assertions=[
                {
                    "type": "glob",
                    "pattern": "reference/hooks/spec-classifier.py",
                    "description": "Spec classifier hook file exists",
                },
            ],
        )

        db.insert_spec(
            id="SPEC-007",
            title="Legacy XML export format",
            description=(
                "The database supported XML export for integration with "
                "external tools. Superseded by JSON export in SPEC-003."
            ),
            status="retired",
            assertions=[],
        )

        # ── Operational Procedures ──

        db.insert_op_procedure(
            id="PROC-001",
            title="Session Wrap-Up",
            description="Standard procedure for ending a work session.",
            steps=[
                "Update specifications in KB to reflect any changes made.",
                "Run assertions to verify no regressions introduced.",
                "Update MEMORY.md with session summary.",
                "Generate handoff prompt via db.insert_session_prompt().",
            ],
            trigger="End of every work session",
            scope="session",
        )

        db.insert_op_procedure(
            id="PROC-002",
            title="Adding a New Feature",
            description="Workflow for implementing a new feature.",
            steps=[
                "Create specification(s) in KB describing the requirement.",
                "Add machine-verifiable assertions to the spec.",
                "Implement the feature in the codebase.",
                "Run assertions — all must PASS.",
                "Promote spec status: specified -> implemented -> verified.",
            ],
            trigger="New feature request from owner",
            scope="feature",
        )

        # ── Session Prompt (handoff example) ──

        db.insert_session_prompt(
            session_id="S001",
            prompt_text=(
                "Continue work on the project. Last session seeded the "
                "knowledge database with example data. Next steps:\n"
                "1. Run assertions to verify seed data is correct.\n"
                "2. Review the web dashboard at localhost:8090.\n"
                "3. Add assertions to any new specs created."
            ),
            context={
                "production_version": "0.1.0",
                "test_count": 7,
                "test_failures": 0,
                "next_tasks": [
                    "Run assertions against seed data",
                    "Review web dashboard",
                    "Begin feature implementation",
                ],
            },
        )

        # ── Summary ──
        summary = db.get_summary()
        print(f"Seeded knowledge database at: {db.db_path}")
        print(f"  Specs:        {summary['spec_total']}")
        print(f"  Procedures:   {summary['op_procedure_total']}")
        print(f"  Prompts:      {summary['session_prompt_pending']}")
        print(f"\nRun assertions:  python reference/assertions.py")
        print(f"Start web UI:    python reference/app.py")

    finally:
        db.close()


if __name__ == "__main__":
    # Default: create knowledge.db alongside this file
    default_path = str(Path(__file__).parent / "knowledge.db")
    seed(default_path)
