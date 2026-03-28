# GroundTruth Reference Implementation

A minimal but complete implementation of the GroundTruth pattern — 4 core tables, machine-verifiable assertions, session hooks, and a read-only web dashboard.

## Quick Start

```bash
# 1. Seed example data
python reference/seed.py

# 2. Run assertions against the seed data
python reference/assertions.py

# 3. Start the web dashboard
pip install flask
python reference/app.py
# → http://localhost:8090
```

## Files

| File | Purpose |
|------|---------|
| `db.py` | Core `KnowledgeDB` class — 4 tables, append-only versioning |
| `assertions.py` | Assertion runner — grep/glob/grep_absent checks |
| `seed.py` | Example data with self-referential assertions |
| `app.py` | Flask read-only web dashboard |
| `hooks/assertion-check.py` | SessionStart hook — runs assertions + handoff |
| `hooks/spec-classifier.py` | UserPromptSubmit hook — spec language detection |
| `hooks/settings.local.json` | Hook registration template |
| `templates/` | Jinja2 templates for the web UI |
| `static/style.css` | Dark theme stylesheet |
| `requirements.txt` | Python dependencies (flask) |

## Schema (4 Core Tables)

- **specifications** — Append-only versioned requirements with JSON assertions column
- **operational_procedures** — Process documentation with ordered steps
- **assertion_runs** — Telemetry from automated codebase checks (prunable)
- **session_prompts** — Event-sourced session-to-session context transfer

Plus supporting views (`current_specifications`, `current_operational_procedures`) and a `change_log` audit trail.

## Extending

This reference includes the core pattern. Common extensions:

- **Tests table** — test artifacts linked to specifications
- **Work items** — trackable units of work with origin/component taxonomy
- **Backlog snapshots** — point-in-time work item priorities
- **Documents** — long-form knowledge under change control
- **Environment config** — deployment-specific settings

See [MEMBASE-4-CLAUDE.md](../MEMBASE-4-CLAUDE.md) for the full pattern with all 9 artifact types.
