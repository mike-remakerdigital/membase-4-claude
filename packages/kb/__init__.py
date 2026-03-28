"""Reusable knowledge-base runtime for Membase-managed projects."""

from .paths import kb_db_path, kb_dir, resolve_project_root
from .scaffold import install_runtime

__all__ = [
    "install_runtime",
    "kb_db_path",
    "kb_dir",
    "resolve_project_root",
]
