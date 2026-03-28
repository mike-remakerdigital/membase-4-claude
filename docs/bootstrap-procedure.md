# Bootstrap Procedure

Use this when evaluating whether a new project can adopt GroundTruth as a real platform rather than a pattern document.

## 1. Initialize

```bash
membase init "Example Project" --dest .
```

## 2. Seed and Verify

```bash
membase kb seed --path ./example-project
membase kb verify --path ./example-project
```

## 3. Confirm Scaffolded Workflow Assets

Check that the generated project contains:

- `.claude/hooks/assertion-check.py`
- `.claude/hooks/spec-classifier.py`
- `.claude/rules/`
- `docs/specs/`
- `docs/tests/`
- `docs/evidence/`
- `docs/runbooks/`
- `memory/handoffs/`
- `tools/knowledge-db/`

## 4. Confirm Operating Contract

Read:

- `CLAUDE.md`
- `.claude/rules/transaction-protocol.md`
- `.claude/rules/stage-0-artifact-sweep.md`
- `.claude/rules/session-handoff.md`

## 5. Configure Bridge Transport

`membase init` does not install a specific bridge runtime yet. Configure the bridge transport in `.mcp.project.json` and project-local rules before using the Prime Builder + Loyal Opposition model.

## 6. First Session Readiness

The project is minimally ready when:

- KB verification passes
- the generated hook files exist
- the first governing specs and tests are created
- the session handoff workflow is understood by the team
