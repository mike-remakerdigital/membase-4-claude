# KB Package

This package contains the reusable Membase knowledge-base runtime.

Current scope:

- managed runtime source under `packages/kb/runtime`
- project installation and copy logic in `packages/kb/scaffold.py`
- path resolution helpers for `membase kb ...` commands

The generated project copy lands in `tools/knowledge-db/`, which preserves the
same local runtime shape used by Agent Red while keeping the upstream source of
truth in this repo.
