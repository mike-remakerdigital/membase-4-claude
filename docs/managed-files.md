# Managed File Contract

GroundTruth uses three ownership classes.

## Upstream-managed

These files are owned by the platform and may be updated by future GroundTruth releases:

- platform CLI
- manifest schema
- hook templates
- bridge runtime/templates
- KB engine/templates
- cloud/test-host scaffolding
- generated `tools/knowledge-db/**` runtime files

## Project-owned

These files belong to a generated project and must not be overwritten by platform updates:

- `src/`
- product-specific tests
- business specifications and content
- secrets
- tenant/customer data
- `tools/knowledge-db/knowledge.db`

## Overlay files

These are project-local configuration layers that sit on top of the platform defaults:

- `membase.project.json`
- `.claude/settings.project.json`
- `.mcp.project.json`

The update engine for later milestones should only update the upstream-managed layer and merge overlays explicitly.

The current KB contract is:

- upstream source of truth: `packages/kb/runtime/`
- generated managed copy: `tools/knowledge-db/`
- project data store: `tools/knowledge-db/knowledge.db`
