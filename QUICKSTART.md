# GroundTruth Quickstart Guide

This quickstart starts with the installable platform path and keeps the older
reference implementation path as a fallback.

GroundTruth is the public product name. During the transition, the CLI remains
`membase` and the manifest remains `membase.project.json`.

Get a working knowledge database in under 5 minutes.

## Prerequisites

- Python 3.10+
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI
- Flask (`pip install Flask`) for the dashboard

## Platform Path

Initialize a new project:

```bash
python -m cli.membase init "Example Project" --dest .
```

Seed and verify the managed KB layer:

```bash
python -m cli.membase kb seed --path ./example-project
python -m cli.membase kb verify --path ./example-project
```

Start the dashboard:

```bash
python -m cli.membase kb serve --path ./example-project
```

This creates:

- `membase.project.json`
- `.claude/settings.project.json`
- `.mcp.project.json`
- `.claude/hooks/assertion-check.py`
- `.claude/hooks/spec-classifier.py`
- `.claude/rules/`
- `docs/specs/`
- `docs/tests/`
- `docs/evidence/`
- `docs/runbooks/`
- `memory/handoffs/`
- `tools/knowledge-db/` managed runtime files
- `tools/knowledge-db/knowledge.db`

Review these immediately after bootstrap:

- `CLAUDE.md`
- `.claude/rules/transaction-protocol.md`
- `.claude/rules/stage-0-artifact-sweep.md`
- `docs/runbooks/bootstrap-checklist.md`

## Reference Path

If you want the original pattern as a runnable example, use the `reference/`
implementation directly.

### 1. Set Up the Database

```bash
cd groundtruth
python reference/seed.py
```

This creates `reference/knowledge.db` with 7 example specs, 2 operational
procedures, and a session handoff prompt.

### 2. Run Assertions

```bash
python reference/assertions.py
```

CLI flags:

- `--pre-build` for CI gating
- `--session-start` for session-start checks
- `--spec SPEC-001` to run a single spec

### 3. Start the Web Dashboard

```bash
python reference/app.py
```

Open http://localhost:8090 to inspect specs, assertion results, procedures, and
change history.

### 4. Configure Claude Code Hooks

Copy the hook settings into your project's `.claude/settings.local.json`:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "type": "command",
        "command": "python reference/hooks/assertion-check.py",
        "timeout": 30000
      }
    ],
    "UserPromptSubmit": [
      {
        "type": "command",
        "command": "python reference/hooks/spec-classifier.py",
        "timeout": 5000
      }
    ]
  }
}
```

### 5. Add to CLAUDE.md

```markdown
### Knowledge Database

All project knowledge lives in the Knowledge Database (`reference/knowledge.db`).
Use the Python API (`reference/db.py`) and never edit SQLite directly.
Web UI: http://localhost:8090
```

## Common Operations

Record a new specification:

```python
db.insert_spec(
    id="SPEC-010",
    title="User authentication via API key",
    description="The system must authenticate API requests via bearer token.",
    spec_type="requirement",
    status="specified",
    assertions=[{
        "type": "grep",
        "pattern": "def authenticate",
        "file": "src/auth.py",
        "description": "Authentication function exists",
    }],
)
```

Update a spec and create a new version:

```python
db.update_spec(
    "SPEC-010",
    changed_by="claude",
    change_reason="implementation complete",
    status="implemented",
)
```

Store a session handoff:

```python
db.insert_session_prompt(
    session_id="S005",
    prompt_text="Continue with SPEC-010 implementation. Auth function written, tests needed.",
    context={"next_tasks": ["Write auth tests", "Update API docs"]},
)
```

## Key Principles

1. Append-only versioning: never update or delete versioned artifacts in place.
2. Machine-verifiable assertions: attach grep and glob checks to important specs.
3. Builder, opposition, and human operator are separate roles with different responsibilities.
4. Stage 0 matters: sweep governing artifacts before proposal work starts.
5. Session handoff: store context for the next session instead of relying on memory.
