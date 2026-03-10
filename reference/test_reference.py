from __future__ import annotations

import subprocess
import sys
import unittest
import uuid
from pathlib import Path


REFERENCE_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(REFERENCE_DIR))

from assertions import run_all_assertions, run_single_assertion
from db import KnowledgeDB


def _test_db_path() -> Path:
    return REFERENCE_DIR / f"test-{uuid.uuid4().hex}.db"


def _cleanup_db(path: Path) -> None:
    for suffix in ("", "-wal", "-shm"):
        candidate = Path(f"{path}{suffix}")
        if candidate.exists():
            candidate.unlink()


class AssertionRunnerTests(unittest.TestCase):
    def test_invalid_regex_returns_failed_result(self) -> None:
        result = run_single_assertion({
            "type": "grep",
            "pattern": "(",
            "file": "README.md",
        })

        self.assertFalse(result["passed"])
        self.assertIn("Invalid regex", result["detail"])

    def test_invalid_regex_does_not_abort_full_run(self) -> None:
        db_path = _test_db_path()
        db = KnowledgeDB(db_path)
        try:
            db.insert_spec(
                id="SPEC-OK",
                title="Valid assertion",
                status="verified",
                assertions=[{
                    "type": "glob",
                    "pattern": "reference/app.py",
                }],
            )
            db.insert_spec(
                id="SPEC-BAD",
                title="Malformed regex",
                status="verified",
                assertions=[{
                    "type": "grep",
                    "pattern": "(",
                    "file": "README.md",
                }],
            )

            summary = run_all_assertions(db)
        finally:
            db.close()
            _cleanup_db(db_path)

        self.assertEqual(summary["total_specs"], 2)
        self.assertEqual(summary["passed"], 1)
        self.assertEqual(summary["failed"], 1)

    def test_missing_spec_cli_exits_nonzero(self) -> None:
        result = subprocess.run(
            [sys.executable, str(REFERENCE_DIR / "assertions.py"), "--spec", "DOES-NOT-EXIST"],
            cwd=REFERENCE_DIR.parent,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ERROR: Spec DOES-NOT-EXIST not found", result.stdout)


class SessionPromptSummaryTests(unittest.TestCase):
    def test_pending_prompt_count_uses_latest_event(self) -> None:
        db_path = _test_db_path()
        db = KnowledgeDB(db_path)
        try:
            db.insert_session_prompt("S001", "prompt one")
            db.insert_session_prompt("S002", "prompt two")
            self.assertEqual(db.get_summary()["session_prompt_pending"], 2)

            db.consume_session_prompt("S001")

            self.assertEqual(db.get_summary()["session_prompt_pending"], 1)
        finally:
            db.close()
            _cleanup_db(db_path)


if __name__ == "__main__":
    unittest.main()
