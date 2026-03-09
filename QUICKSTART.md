# Membase Quickstart Guide

Get a working knowledge database in under 5 minutes.

## Prerequisites

- Python 3.10+
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI
- Flask (`pip install flask`) — only for the web dashboard

## 1. Set Up the Database

Copy the `reference/` directory into your project, or work directly from this repo:

```bash
# Option A: Copy into your project
cp -r reference/ /path/to/your/project/knowledge-db/

# Option B: Work from this repo
cd membase-4-claude
```

Seed the database with example data:

```bash
python reference/seed.py
```

This creates `reference/knowledge.db` with 7 example specs, 2 operational procedures, and a session handoff prompt.

## 2. Run Assertions

```bash
python reference/assertions.py
```

The assertions check the reference files themselves — you should see PASS results for verified/implemented specs and expected FAILs for specified-only specs.

CLI flags:
- `--pre-build` — exit code 1 on any failure (CI gate)
- `--session-start` — used by the SessionStart hook
- `--spec SPEC-001` — run assertions for a single spec

## 3. Start the Web Dashboard

```bash
pip install flask
python reference/app.py
```

Open http://localhost:8090 — you'll see the knowledge database with specs, assertion results, procedures, and change history.

## 4. Configure Claude Code Hooks

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

**SessionStart hook** runs assertions automatically at the start of every session and injects results as context. It also reads any pending session handoff prompts.

**UserPromptSubmit hook** detects specification language ("must include", "should support", numbered requirements) and reminds Claude to record specs before implementing.

## 5. Add to CLAUDE.md

Add these lines to your project's `CLAUDE.md`:

```markdown
### Knowledge Database

All project knowledge lives in the Knowledge Database (`reference/knowledge.db`).
Use the Python API (`reference/db.py`) — never edit SQLite directly.
Web UI: http://localhost:8090

Key methods:
- `db.insert_spec()` — record a new specification
- `db.update_spec()` — create a new version of an existing spec
- `db.insert_op_procedure()` — record an operational procedure
- `db.insert_session_prompt()` — store context for the next session

Workflow: Specification → Implementation → Assertion → Verification
```

## 6. Start Using It

In your next Claude Code session:

```
Read reference/db.py and understand the Knowledge Database API.
Then read the existing specs with db.list_specs().
```

### Common Operations

**Record a new specification:**
```python
db.insert_spec(
    spec_id="SPEC-010",
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

**Update a spec (creates a new version):**
```python
db.update_spec("SPEC-010", status="implemented")
```

**Record a session handoff:**
```python
db.insert_session_prompt(
    session_id="S005",
    prompt_text="Continue with SPEC-010 implementation. Auth function written, tests needed.",
    context={"next_tasks": ["Write auth tests", "Update API docs"]},
)
```

**Run assertions programmatically:**
```python
from assertions import run_all_assertions
summary = run_all_assertions(db, triggered_by="manual")
print(f"Passed: {summary['passed']}, Failed: {summary['failed']}")
```

## Scaling Up

When your project outgrows 4 tables, add more artifact types:

1. **Tests** — link test artifacts to specifications for traceability
2. **Work items** — track implementation tasks with origin/component taxonomy
3. **Documents** — store long-form knowledge under change control
4. **Environment config** — manage deployment-specific settings

See [MEMBASE-4-CLAUDE.md](MEMBASE-4-CLAUDE.md) for the full 9-table pattern.

## Key Principles

1. **Append-only** — never UPDATE or DELETE versioned artifacts. Every change creates a new version.
2. **Machine-verifiable** — attach grep/glob assertions to specs. "Claude remembers" becomes "Claude proves."
3. **Claude writes, human observes** — all mutations through the Python API, not through SQLite directly.
4. **Session handoff** — store context for the next session to eliminate cold-start friction.
5. **Pruning is for telemetry, not artifacts** — assertion runs can be pruned; specs and procedures cannot.
