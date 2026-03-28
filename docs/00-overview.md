# GroundTruth v1 Overview

GroundTruth is the public product name for the platform previously labeled Membase. It is transitioning from a pattern/reference repository into an installable bootstrap platform.

The v1 platform contract has four immediate goals:

1. initialize a new project with a versioned manifest,
2. install a managed knowledge-base runtime into `tools/knowledge-db`,
3. scaffold the builder/opposition workflow assets required for a governed project,
4. provide a CLI for prerequisite checks, seeding, verification, and dashboard serving,
5. establish the managed vs project-owned boundary before more platform code is extracted.

This repo still includes the `reference/` implementation as the runnable pattern baseline. The platform layer now grows alongside it until the reusable infrastructure is fully promoted out of downstream projects.

Current M0/M1 scope:

- `packages/kb/runtime` is the upstream source of truth for the managed KB layer.
- `packages/platform/scaffold.py` is the source of truth for generated workflow assets.
- `membase init` installs that runtime into new projects.
- `membase init` now also generates hook, rule, handoff, and bootstrap docs for a three-party workflow.
- `membase kb init|seed|verify|serve` provides the first end-to-end platform workflow.
- Agent Red remains the downstream proving ground; see `docs/upstream-upkeep.md` for promotion rules.
