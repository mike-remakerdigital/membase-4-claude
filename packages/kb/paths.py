from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

DEFAULT_KB_DIR = Path("tools") / "knowledge-db"
DEFAULT_DB_NAME = "knowledge.db"
DEFAULT_WEB_PORT = 8090


def resolve_project_root(project_root: str | Path | None = None) -> Path:
    candidate = project_root or os.environ.get("MEMBASE_PROJECT_ROOT") or "."
    return Path(candidate).resolve()


def manifest_path(project_root: str | Path | None = None) -> Path:
    return resolve_project_root(project_root) / "membase.project.json"


def load_manifest(project_root: str | Path | None = None) -> dict[str, Any] | None:
    path = manifest_path(project_root)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def kb_relative_dir(project_root: str | Path | None = None) -> Path:
    manifest = load_manifest(project_root)
    if manifest:
        kb = manifest.get("knowledge_base")
        if isinstance(kb, dict):
            root = kb.get("root")
            if isinstance(root, str) and root.strip():
                return Path(root)
    return DEFAULT_KB_DIR


def kb_dir(project_root: str | Path | None = None) -> Path:
    root = resolve_project_root(project_root)
    return root / kb_relative_dir(root)


def kb_db_path(project_root: str | Path | None = None) -> Path:
    root = resolve_project_root(project_root)
    manifest = load_manifest(root)
    if manifest:
        kb = manifest.get("knowledge_base")
        if isinstance(kb, dict):
            db_path = kb.get("db_path")
            if isinstance(db_path, str) and db_path.strip():
                return root / Path(db_path)
    return kb_dir(root) / DEFAULT_DB_NAME
