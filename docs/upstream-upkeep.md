# Upstream Upkeep Workflow

GroundTruth is the upstream-managed platform repo. Agent Red is the proving ground.
Reusable improvements should move upstream on purpose, not by accident.

## Cadence

- Run an upstream scan whenever Agent Red lands a meaningful infrastructure change.
- Do a broader consolidation pass before cutting any GroundTruth release.

## Source-to-upstream map

- `Agent Red/tools/knowledge-db/` -> `membase/packages/kb/runtime/`
- `Agent Red/.claude/hooks/` -> `membase/packages/hooks/`
- `Agent Red/bridge runtime and poller behavior` -> `membase/packages/bridge/`
- `Agent Red/setup runbooks and operator guides` -> `membase/docs/`
- `Agent Red/bootstrapable templates or starter artifacts` -> `membase/templates/`

## Scan procedure

1. Compare the candidate downstream area against the upstream source-of-truth area.
2. Classify each delta as:
   - reusable platform capability
   - downstream-specific product logic
   - experiment or temporary mitigation
3. Promote only the reusable slice.
4. Verify the promoted slice in a throwaway GroundTruth-generated project before closing the patch.

## Suggested commands

```powershell
git -C "E:\Claude-Playground\CLAUDE-PROJECTS\Agent Red Customer Engagement" log --stat -- tools/knowledge-db .claude/hooks scripts
git diff --no-index `
  "E:\Claude-Playground\CLAUDE-PROJECTS\Agent Red Customer Engagement\tools\knowledge-db" `
  "E:\Claude-Playground\CLAUDE-PROJECTS\membase-4-claude\packages\kb\runtime"
```

Use `git diff --no-index` the same way for hooks, bridge assets, docs, and templates.

## Promotion rules

- Keep the upstream package generic. Strip Agent Red product names, tenant IDs, and environment-specific values.
- Preserve the managed-vs-project-owned boundary. Upstream code can overwrite managed files; it must not trample project content.
- Record any new manifest fields or migration expectations when a promoted change alters generated project shape.
- Prefer additive migrations over destructive rewrites.

## Verification checklist

- `python -m cli.membase init "Smoke Project" --dest .codex-smoke --force`
- `python -m cli.membase kb seed --path .codex-smoke\smoke-project`
- `python -m cli.membase kb verify --path .codex-smoke\smoke-project`
- If the change touches the dashboard or Flask runtime, verify app creation or a test-client request.

## Release expectation

Every promoted upstream change should leave three artifacts behind:

- code in the upstream package or template layer
- docs describing the managed behavior
- a local verification record in the commit or PR notes
