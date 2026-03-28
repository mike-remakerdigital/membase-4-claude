from __future__ import annotations

import shutil
from pathlib import Path

from .paths import kb_db_path, kb_dir, resolve_project_root

RUNTIME_DIR = Path(__file__).parent / "runtime"


def _iter_runtime_files() -> list[Path]:
    return [
        path
        for path in sorted(RUNTIME_DIR.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    ]


def install_runtime(project_root: str | Path, force: bool = False) -> list[Path]:
    root = resolve_project_root(project_root)
    target_dir = kb_dir(root)
    target_dir.mkdir(parents=True, exist_ok=True)

    copied: list[Path] = []
    for source_path in _iter_runtime_files():
        relative = source_path.relative_to(RUNTIME_DIR)
        target_path = target_dir / relative
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if target_path.exists() and not force:
            continue
        shutil.copy2(source_path, target_path)
        copied.append(target_path)

    from .runtime.db import KnowledgeDB

    db = KnowledgeDB(kb_db_path(root))
    db.close()
    return copied
