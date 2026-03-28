from __future__ import annotations

import json
import shutil
import unittest
import uuid
from argparse import Namespace
from pathlib import Path

from cli import membase
from packages.kb.paths import kb_db_path
from packages.kb.runtime import app as kb_app
from packages.kb.runtime import assertions as kb_assertions


class MembaseBootstrapTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scratch_root = Path(__file__).resolve().parent.parent / ".test-tmp"
        self.root = self.scratch_root / uuid.uuid4().hex
        self.root.mkdir(parents=True, exist_ok=True)
        self.project_name = "Smoke Project"
        self.slug = "smoke-project"
        self.project_root = self.root / self.slug

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def _init_project(self) -> None:
        exit_code = membase.run_init(
            Namespace(project_name=self.project_name, dest=str(self.root), force=False)
        )
        self.assertEqual(exit_code, 0)

    def test_init_installs_manifest_and_kb_runtime(self) -> None:
        self._init_project()

        manifest_path = self.project_root / "membase.project.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        self.assertEqual(manifest["project_slug"], self.slug)
        self.assertEqual(manifest["knowledge_base"]["root"], "tools/knowledge-db")
        self.assertEqual(
            manifest["workflow"]["stages"],
            [
                "stage-0-artifact-sweep",
                "proposal",
                "proposal-challenge",
                "implementation",
                "implementation-challenge",
            ],
        )
        self.assertIn("observed-reality", manifest["evidence_surfaces"])
        self.assertEqual(manifest["session_handoff"]["handoff_dir"], "memory/handoffs")
        self.assertTrue((self.project_root / "tools" / "knowledge-db" / "db.py").exists())
        self.assertTrue(
            (self.project_root / "tools" / "knowledge-db" / "templates" / "dashboard.html").exists()
        )
        self.assertTrue((self.project_root / ".claude" / "hooks" / "assertion-check.py").exists())
        self.assertTrue((self.project_root / ".claude" / "hooks" / "spec-classifier.py").exists())
        self.assertTrue(
            (self.project_root / ".claude" / "rules" / "transaction-protocol.md").exists()
        )
        self.assertTrue(
            (self.project_root / "memory" / "handoffs" / "NEXT_SESSION_TEMPLATE.md").exists()
        )
        self.assertTrue((self.project_root / "docs" / "evidence" / "README.md").exists())
        self.assertTrue((self.project_root / ".gitignore").exists())

        settings = json.loads(
            (self.project_root / ".claude" / "settings.project.json").read_text(encoding="utf-8")
        )
        hooks = settings["hooks"]
        self.assertEqual(
            hooks["SessionStart"][0]["command"],
            "python .claude/hooks/assertion-check.py",
        )
        self.assertEqual(
            hooks["UserPromptSubmit"][0]["command"],
            "python .claude/hooks/spec-classifier.py",
        )

        claude_md = (self.project_root / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("docs/evidence/", claude_md)
        self.assertIn("docs/bridge/", claude_md)

    def test_seed_and_verify_pass_for_generated_project(self) -> None:
        self._init_project()

        seed_exit = membase.run_kb_seed(Namespace(path=str(self.project_root), force=False))
        self.assertEqual(seed_exit, 0)

        summary = kb_assertions.verify_project(
            project_root=self.project_root,
            db_path=kb_db_path(self.project_root),
        )
        self.assertEqual(summary["failed"], 0)
        self.assertEqual(summary["passed"], 4)
        self.assertEqual(summary["skipped"], 3)

    def test_dashboard_app_renders_when_flask_is_available(self) -> None:
        self._init_project()
        seed_exit = membase.run_kb_seed(Namespace(path=str(self.project_root), force=False))
        self.assertEqual(seed_exit, 0)

        try:
            app = kb_app.create_app(kb_db_path(self.project_root))
        except RuntimeError as exc:
            self.skipTest(str(exc))

        client = app.test_client()
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Dashboard", response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
