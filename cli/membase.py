from __future__ import annotations

import argparse
import json
import platform
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from packages.kb.paths import DEFAULT_KB_DIR, DEFAULT_WEB_PORT, kb_db_path, kb_dir, resolve_project_root
from packages.kb.runtime import app as kb_app
from packages.kb.runtime import assertions as kb_assertions
from packages.kb.runtime import seed as kb_seed
from packages.kb.runtime.db import KnowledgeDB
from packages.kb.scaffold import install_runtime
from packages.platform.scaffold import install_project_scaffold

VERSION = "0.1.0"
DEFAULT_MODULES = [
    "kb",
    "hooks",
    "bridge",
    "starter-artifacts",
]


@dataclass
class CheckResult:
    name: str
    required: bool
    found: bool
    detail: str


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "new-project"


def project_manifest_path(base_path: Path) -> Path:
    return base_path / "membase.project.json"


def build_manifest(project_name: str, slug: str) -> dict:
    return {
        "schema_version": 1,
        "platform_version": VERSION,
        "project_slug": slug,
        "display_name": project_name,
        "owner": "",
        "workspace_os": platform.system().lower(),
        "cloud": {
            "provider": "azure",
            "subscription_name": "",
            "resource_group_prefix": slug,
            "location": "eastus",
        },
        "repos": {
            "git_remote": "",
            "github_org": "",
            "github_repo": slug,
        },
        "agents": {
            "claude_enabled": True,
            "codex_enabled": True,
            "bridge_enabled": True,
        },
        "workflow": {
            "model": "prime-builder-loyal-opposition-human",
            "human_operator_required": True,
            "pre_proposal_artifact_sweep": True,
            "stages": [
                "stage-0-artifact-sweep",
                "proposal",
                "proposal-challenge",
                "implementation",
                "implementation-challenge",
            ],
        },
        "bridge": {
            "enabled": True,
            "transport": "configure-per-project",
            "message_contract": "subject-body-priority-correlation-artifact-refs",
        },
        "evidence_surfaces": [
            "specifications",
            "tests",
            "system-artifacts",
            "observed-reality",
        ],
        "session_handoff": {
            "memory_path": "memory/MEMORY.md",
            "handoff_dir": "memory/handoffs",
            "kb_prompt_table": "session_prompts",
            "required": True,
        },
        "managed_modules": DEFAULT_MODULES,
        "overrides": {
            "claude_settings": ".claude/settings.project.json",
            "mcp": ".mcp.project.json",
        },
        "knowledge_base": {
            "root": str(DEFAULT_KB_DIR).replace("\\", "/"),
            "db_path": str((DEFAULT_KB_DIR / "knowledge.db")).replace("\\", "/"),
            "seed_profile": "starter",
            "web_port": DEFAULT_WEB_PORT,
        },
    }


def check_command(name: str, commands: list[str], required: bool) -> CheckResult:
    for command in commands:
        path = shutil.which(command)
        if path:
            return CheckResult(name=name, required=required, found=True, detail=path)
    missing = f"not found ({', '.join(commands)})"
    return CheckResult(name=name, required=required, found=False, detail=missing)


def run_doctor(_args: argparse.Namespace) -> int:
    checks = [
        check_command("git", ["git"], True),
        CheckResult("python", True, True, sys.executable),
        check_command("node", ["node"], True),
        check_command("npm", ["npm"], True),
        check_command("docker", ["docker"], True),
        check_command("az", ["az"], True),
        check_command("gh", ["gh"], False),
        check_command("powershell", ["powershell", "pwsh"], platform.system() == "Windows"),
        check_command("claude", ["claude"], False),
        check_command("codex", ["codex"], False),
    ]

    print(f"GroundTruth doctor ({VERSION})")
    print("")
    failures = 0
    for check in checks:
        status = "OK" if check.found else ("WARN" if not check.required else "FAIL")
        if status == "FAIL":
            failures += 1
        required = "required" if check.required else "optional"
        print(f"{status:4}  {check.name:12} {required:8} {check.detail}")

    print("")
    if failures:
        print(f"Doctor failed: {failures} required dependency check(s) missing.")
        return 1

    print("Doctor passed.")
    return 0


def write_text(path: Path, content: str, force: bool) -> None:
    if path.exists() and not force:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, payload: dict, force: bool) -> None:
    if path.exists() and not force:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _bootstrap_project_files(target_dir: Path, project_name: str, force: bool) -> None:
    write_json(project_manifest_path(target_dir), build_manifest(project_name, target_dir.name), force)


def run_init(args: argparse.Namespace) -> int:
    slug = slugify(args.project_name)
    target_dir = (Path(args.dest).resolve() / slug)
    target_dir.mkdir(parents=True, exist_ok=True)

    if any(target_dir.iterdir()) and not args.force:
        print(f"Refusing to initialize into non-empty directory: {target_dir}")
        print("Use --force to write scaffold files into an existing directory.")
        return 1

    for relative in [
        ".claude",
        "docs",
        "memory",
        "scripts",
        "src",
        "tests",
    ]:
        (target_dir / relative).mkdir(parents=True, exist_ok=True)

    _bootstrap_project_files(target_dir, args.project_name, args.force)
    scaffolded = install_project_scaffold(
        target_dir,
        project_name=args.project_name,
        slug=slug,
        kb_root=str(DEFAULT_KB_DIR).replace("\\", "/"),
        kb_db_path=str((DEFAULT_KB_DIR / "knowledge.db")).replace("\\", "/"),
        force=args.force,
    )
    copied = install_runtime(target_dir, force=args.force)

    print(f"Initialized GroundTruth project scaffold at {target_dir}")
    print(f"Manifest: {project_manifest_path(target_dir)}")
    print(f"KB runtime: {kb_dir(target_dir)}")
    print(f"Workflow scaffold files copied: {len(scaffolded)}")
    print(f"KB files copied: {len(copied)}")
    print("")
    print("Next steps:")
    print(f"  membase kb seed --path {target_dir}")
    print(f"  membase kb verify --path {target_dir}")
    return 0


def run_status(args: argparse.Namespace) -> int:
    base_path = resolve_project_root(args.path)
    manifest_path = project_manifest_path(base_path)
    if not manifest_path.exists():
        print(f"No membase.project.json found at {manifest_path}")
        return 1

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    db_path = kb_db_path(base_path)
    runtime_path = kb_dir(base_path)
    print("GroundTruth project status")
    print("")
    print(f"Project:          {payload.get('display_name', '')}")
    print(f"Slug:             {payload.get('project_slug', '')}")
    print(f"Platform version: {payload.get('platform_version', '')}")
    print(f"Workspace OS:     {payload.get('workspace_os', '')}")
    print(f"Modules:          {', '.join(payload.get('managed_modules', []))}")
    workflow = payload.get("workflow", {})
    if isinstance(workflow, dict):
        print(f"Workflow model:   {workflow.get('model', '')}")
    handoff = payload.get("session_handoff", {})
    if isinstance(handoff, dict):
        print(f"Handoff dir:      {handoff.get('handoff_dir', '')}")
    print(f"KB runtime:       {runtime_path}")
    print(f"KB database:      {db_path}")
    print(f"KB present:       {'yes' if runtime_path.exists() else 'no'}")
    return 0


def run_kb_init(args: argparse.Namespace) -> int:
    base_path = resolve_project_root(args.path)
    base_path.mkdir(parents=True, exist_ok=True)
    copied = install_runtime(base_path, force=args.force)
    print(f"Installed KB runtime at {kb_dir(base_path)}")
    print(f"KB database: {kb_db_path(base_path)}")
    print(f"Files copied: {len(copied)}")
    return 0


def run_kb_seed(args: argparse.Namespace) -> int:
    base_path = resolve_project_root(args.path)
    runtime_dir = kb_dir(base_path)
    if not (runtime_dir / "db.py").exists():
        print(f"KB runtime not found at {runtime_dir}")
        print("Run `membase kb init` first.")
        return 1

    db_path = kb_db_path(base_path)
    try:
        summary = kb_seed.seed(db_path=db_path, force=args.force)
    except RuntimeError as exc:
        print(str(exc))
        return 1

    print(f"Seeded knowledge database at: {db_path}")
    print(f"  Specs:        {summary['spec_total']}")
    print(f"  Procedures:   {summary['op_procedure_total']}")
    print(f"  Prompts:      {summary['session_prompt_pending']}")
    return 0


def run_kb_verify(args: argparse.Namespace) -> int:
    base_path = resolve_project_root(args.path)
    db_path = kb_db_path(base_path)
    if not db_path.exists():
        print(f"KB database not found at {db_path}")
        print("Run `membase kb init` and `membase kb seed` first.")
        return 1

    db = KnowledgeDB(db_path)
    try:
        current_summary = db.get_summary()
    finally:
        db.close()

    if current_summary["spec_total"] == 0:
        print(f"KB at {db_path} contains no specifications.")
        print("Run `membase kb seed` or add project-specific KB records before verification.")
        return 1

    summary = kb_assertions.verify_project(
        project_root=base_path,
        db_path=db_path,
        triggered_by=args.triggered_by,
        spec_id=args.spec,
    )
    kb_assertions.print_summary(summary)
    if "error" in summary:
        return 1
    return 1 if summary.get("failed", 0) > 0 else 0


def run_kb_serve(args: argparse.Namespace) -> int:
    base_path = resolve_project_root(args.path)
    try:
        return kb_app.serve(
            db_path=kb_db_path(base_path),
            host=args.host,
            port=args.port,
            debug=not args.no_debug,
        )
    except RuntimeError as exc:
        print(str(exc))
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="GroundTruth bootstrap platform CLI (compatible command: membase)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="Check local prerequisites")
    doctor.set_defaults(func=run_doctor)

    init = subparsers.add_parser("init", help="Create a new GroundTruth project scaffold")
    init.add_argument("project_name", help="Display name for the new project")
    init.add_argument("--dest", default=".", help="Parent directory for the new project")
    init.add_argument("--force", action="store_true", help="Write scaffold files into a non-empty target")
    init.set_defaults(func=run_init)

    status = subparsers.add_parser("status", help="Show the local project manifest status")
    status.add_argument("--path", default=".", help="Project root path")
    status.set_defaults(func=run_status)

    kb = subparsers.add_parser("kb", help="Manage the GroundTruth knowledge base runtime")
    kb_subparsers = kb.add_subparsers(dest="kb_command", required=True)

    kb_init = kb_subparsers.add_parser("init", help="Install or refresh the KB runtime in a project")
    kb_init.add_argument("--path", default=".", help="Project root path")
    kb_init.add_argument("--force", action="store_true", help="Overwrite existing managed KB files")
    kb_init.set_defaults(func=run_kb_init)

    kb_seed_parser = kb_subparsers.add_parser("seed", help="Seed the KB with starter data")
    kb_seed_parser.add_argument("--path", default=".", help="Project root path")
    kb_seed_parser.add_argument("--force", action="store_true", help="Allow re-seeding an existing KB")
    kb_seed_parser.set_defaults(func=run_kb_seed)

    kb_verify = kb_subparsers.add_parser("verify", help="Run KB assertions against the project")
    kb_verify.add_argument("--path", default=".", help="Project root path")
    kb_verify.add_argument("--spec", default=None, help="Run a single spec ID")
    kb_verify.add_argument(
        "--triggered-by",
        default="manual",
        choices=["manual", "pre-build", "session-start"],
        help="Assertion trigger context",
    )
    kb_verify.set_defaults(func=run_kb_verify)

    kb_serve = kb_subparsers.add_parser("serve", help="Serve the KB dashboard")
    kb_serve.add_argument("--path", default=".", help="Project root path")
    kb_serve.add_argument("--host", default="127.0.0.1")
    kb_serve.add_argument("--port", type=int, default=DEFAULT_WEB_PORT)
    kb_serve.add_argument("--no-debug", action="store_true", help="Disable Flask debug mode")
    kb_serve.set_defaults(func=run_kb_serve)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
