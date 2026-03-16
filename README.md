# Membase for Claude

**Persistent, version-controlled, self-auditing project memory for Claude Code — backed by an append-only SQLite database.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> Claude Code needed a project knowledge database, so it built one.

---

## What This Is

Membase is a **pattern** (not a library) for giving Claude Code durable memory that survives across sessions. It replaces fragile markdown backlogs with a structured, append-only SQLite database where every change is versioned and every claim is machine-verifiable.

Developed across 189 sessions on a commercial SaaS project, it solves three problems that emerge in long-running Claude Code projects:

1. **Context window saturation** — long sessions accumulate stale context that biases decisions.
2. **Session boundary amnesia** — each new session starts cold; CLAUDE.md and MEMORY.md help but drift over time.
3. **Undetected regression** — code changes silently break previously-verified behavior with no automated signal.

## How It Works

Claude is the **sole writer**. The human observes through a read-only web UI. The database stores 9 managed artifact types — specifications, tests, test plans, work items, backlog snapshots, operational procedures, documents, environment config, and testable elements — all under append-only change control. Machine-verifiable assertions (grep/glob checks against the actual codebase) run automatically at session start, catching regressions before work begins. A quality dashboard displays 4 key metrics (assertion coverage, test traceability, defect velocity, defect escape rate) at session start. A session handoff system eliminates cold-start friction by having each session store context for the next one.

The markdown files (CLAUDE.md, MEMORY.md, topic files) still matter — they store rules, preferences, and operational patterns that don't fit a relational model. The database complements them with formal artifacts and machine-verifiable truth. The governance principle is simple: **if Claude references something, it must exist; if it exists, it must be under change control; if it's under change control, its history must be retrievable.** Key milestones include converting the entire Master Test Plan to live-only external interface testing (S133), achieving 100% machine-verifiable assertion pass rate across 1,621 assertions on 2,016 specifications (S146–S173), implementing automated assertion pruning to keep the database compact (S158), and formalizing repeatable workflows as executable Claude Code skills (S189).

## Getting Started

### Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) (CLI)
- Python 3.10+
- SQLite 3 (included with Python)
- Flask (for the optional read-only web UI)

### Usage

1. Download [`MEMBASE-4-CLAUDE.md`](MEMBASE-4-CLAUDE.md) into your project
2. Ask Claude to read it:

```
Read MEMBASE-4-CLAUDE.md and set up the Membase knowledge database for this project.
```

That's it. The file contains the complete implementation pattern — schema, API, assertion runner, session hooks, governance principles, and web UI — with enough detail for Claude to reproduce it and adapt it to your project.

## Commit-Everything Policy

All project files created locally must be committed. Before pushing:

- `git add -A`
- `git status --short` must be empty

This prevents core artifacts from living only on disk.

## Quick Start

```bash
# Seed example data, run assertions, start web UI
python reference/seed.py
python reference/assertions.py
pip install flask && python reference/app.py
```

See [`QUICKSTART.md`](QUICKSTART.md) for the full walkthrough including hook configuration and CLAUDE.md integration.

## What's in This Repo

| File | Purpose |
|------|---------|
| [`MEMBASE-4-CLAUDE.md`](MEMBASE-4-CLAUDE.md) | Complete implementation guide (the pattern document Claude reads) |
| [`QUICKSTART.md`](QUICKSTART.md) | 5-minute bootstrap guide |
| [`reference/`](reference/) | Runnable reference implementation — 4 core tables, assertions, hooks, web UI |
| [`README.md`](README.md) | This file — context and motivation |
| [`LICENSE`](LICENSE) | MIT License |

## Glossary of Key Terms

These terms have specific meanings in the Membase pattern. Understanding them is essential for working with the system.

| Term | Definition |
|------|-----------|
| **Specification** | A requirement — a business decision that affects customers or the business. Functions as a decision log (what was agreed and why), not a build specification. |
| **Test** | A testable assertion derived from a specification. Must produce an unambiguous PASS/FAIL. |
| **Test Plan** | An orchestrating artifact: ordered test phases with gate criteria. References test IDs without duplicating content. |
| **Work Item** | A unit of work classified by origin (regression, defect, new, hygiene) and component. |
| **Backlog Snapshot** | A point-in-time snapshot of active work items. A frozen record, not a living document. |
| **Assertion** | A machine-verifiable check (grep/glob) attached to a specification. Turns "Claude remembers" into "Claude proves." |
| **Phantom Artifact** | A concept referenced as if tracked, but with no backing storage or change control. The anti-pattern this system eliminates. |
| **Orchestrating Artifact** | An artifact that composes others by reference (ID only), never by content duplication. |
| **Governance Principle** | A process rule (GOV-\*) governing human-AI collaboration. 18 numbered rules (GOV-01–GOV-18) plus 3 architectural principles (Artifact Inventory, Orchestrating Artifact, Spec Litmus Test). Discovered through use, not designed upfront. |
| **Append-Only** | The change control discipline: no UPDATE, no DELETE. Every mutation creates a new versioned row. |
| **Session Handoff** | A structured prompt stored by one session for the next, eliminating cold-start friction. |
| **Protected Behavior** | A specification carrying machine-verifiable assertions that must always pass. |
| **Testable Element** | A UI component, form field, or interactive element inventoried for test coverage tracking. Stored in the `testable_elements` table with dimensional taxonomy (14 categories A–N). |
| **Quality Dashboard** | A 4-metric display rendered at session start: assertion coverage, test traceability, defect velocity, and defect escape rate. Provides immediate quality signal before work begins. |
| **Skill** | A Claude Code SKILL.md file that encodes a repeatable workflow as an executable playbook. Stored in `.claude/skills/<name>/SKILL.md`. Skills mechanize governance chains (e.g., GOV-12 + GOV-13) that previously relied on Claude's self-discipline. |

See the [full glossary with examples](MEMBASE-4-CLAUDE.md#glossary) in the implementation guide.

## Benefits & Milestones

Membase was not designed upfront — it evolved through real project needs across 189 sessions. The milestones below trace how each capability was added in response to a specific problem.

### Evolution Timeline

| Session | Problem Encountered | Capability Added |
|---------|-------------------|-----------------|
| S1–S95 | Markdown backlogs drift; concepts referenced but not tracked | — (markdown-only era) |
| S96 | No machine-verifiable truth about what's implemented | **Knowledge Database** — append-only SQLite, assertions, web UI |
| S104–S106 | Requirements scattered across 90 session transcripts | **Specification Discipline** — 871 specs extracted, governance principles crystallized |
| S109 | No way to measure which specs have tests | **Test Coverage** — `test_coverage` table, 1,230 test-to-spec mappings |
| S110 | Topic files contradict each other and the database | **GOV-08** — 30 topic files migrated to KB documents under change control |
| S112 | No way to measure which specs have tests | **Test Coverage Sprint** — 1,053 new tests, spec coverage 26% → 59% |
| S113–S114 | "Backlog" and "test plan" referenced but not actually tracked artifacts | **Artifact System Redesign** — 5 new tables, phantom artifacts eliminated |
| S116–S117 | Claude implements before recording specs from owner requirements | **GOV-09 + GOV-10** — spec-language detection hook (S116), tests must exercise production interfaces (S117) |
| S128 | Work items created without tests; no lifecycle tracking | **GOV-12** — work item creation triggers test creation; stage-gate transitions |
| S129 | Tests orphaned from test plan phases | **GOV-13** — test artifacts must be assigned to at least one test plan phase upon creation |
| S131 | UI changes break tests silently; tests fixed without approval; deploys without approval | **GOV-14–16** — UI element test sync, test fix approval gate, deployment approval gate |
| S133 | Mocked/inspection tests give false confidence; can't verify production behavior | **SPEC-1649** — Master Test Plan converted to live-only (13 active phases, 3 removed). All tests exercise external interfaces. |
| S135 | No systematic inventory of what should be tested in the UI | **SPEC-1652/1653** — Testable element inventory (520 elements), 4-phase quality cycle, dimensional taxonomy (14 categories A–N) |
| S135–S144 | Shallow live E2E tests miss real bugs | **936 live E2E tests** across 3 admin consoles (Standalone 576, Provider 264, Shopify 96), all exercising real staging APIs |
| S145 | No visibility into quality metrics at session start | **Quality Dashboard** (SPEC-1659/1660) — 4 metrics at every session start: assertion coverage, test traceability, defect velocity, defect escape rate |
| S146–S150 | 87% of specs lack machine-verifiable assertions | **Batch assertion generation** — 3-tier strategy (grep in known file, glob, keyword mapping). Coverage 12.9% → 99.5%. |
| S153 | Specs classified as "not yet implemented" that are actually implemented | **Verification mega-session** — 400 spec promotions, 148 retirements, GOV-18 (Assertion Quality Standard) |
| S157 | SPA console shares auth layer with tenant endpoints | **SPEC-1667/1668** — Complete SPA platform admin auth isolation with dedicated Cosmos collection and key prefix |
| S158 | assertion_runs table grows unboundedly (~230K rows, ~93 MB) | **Assertion pruning** — keeps latest 5 runs per spec, automated in SessionStart hook. DB 93 → 18 MB. Batch description enrichment (885 specs). |
| S161 | Quality evaluation exposed auth, rate-limit, and CI gaps | **Quality evaluation remediation** — auth hardening (30-min inactivity logout, session binding, X-Frame-Options), rate limit backend consolidation, CI/CD tooling (GitHub Actions, Makefile) |
| S165–S166 | Need zero-backend UI development and testing | **Mock dev environment** — `npm run dev:mock` with in-memory store + fixture data. 527 mock E2E tests (SPEC-1706) across 14 test files, zero-backend testing. |
| S169 | 5,085-line monolith file blocks team scalability | **Superadmin API split** — monolith decomposed into 5 domain submodules. Key lesson: Python `from module import var` creates a local binding invisible to `mock.patch` — use module-attribute access pattern instead. |
| S173 | 74 stale assertion failures after monolith split | **Deep hygiene** — all 74 failures traced to stale file paths from S169 package split. 50 specs remapped to correct submodules, 17 specs retired. Final state: 1,621/1,621 assertions passing. |
| S174–S175 | Single-tenant architecture won't scale to 680 tenants | **680-tenant infrastructure scaling** — Redis cache, sharded rate limiting, 4 Uvicorn workers, global SSE, tenant metadata cache, LRU guards, per-tier entitlements. 90 tests. |
| S176 | Redis connection failures in container environment | **Redis connectivity fix** — `username=None` required in `Redis.from_url()` for Azure Cache for Redis. v1.83.0 deployed. |
| S177–S179 | Rubber-stamp tests pass without verifying real behavior | **GOV-18 enforcement** — 11 rubber-stamp tests replaced with behavioral tests exercising actual API responses, not just "status 200." |
| S178 | No integration ecosystem plan beyond core product | **P1 Integration Ecosystem** — 18 specifications (SPEC-1761–1778) for MCP agents, Shopify deep integration, Stripe billing, and AGNTCY multi-agent protocol. |
| S180 | Provider Console missing critical admin workflows | **Provider Console walkthrough** — 3 fixes (Co-Pilot Knowledge repo, email lookup, tenant display names). v1.84.0 production deploy. |
| S181–S183 | AI agents run in-process; can't scale independently | **AGNTCY multi-agent containerization** — 7 agent containers deployed (IC, KR, RG, escalation, analytics, critic, co-pilot). NATS JetStream provisioned. AGNTCY SDK wired. Fail-loud dispatch (SPEC-1780). v1.86.0. |
| S184 | Rate limits hard-coded per tier; no data-driven tuning | **Data-driven rate limiting** — Ramp-to-overload test derived 1,380 RPM safe capacity. Uniform 300 RPM/tenant. Per-tier cap enforcement removed. RATE_LIMIT_DISABLED env var. v1.87.0. |
| S185 | 5 assertion regressions accumulated across S184 changes | **Audit session** — all regressions traced to rate limit constant changes (500→300) and glob path fixes. 8 stale WIs resolved. Production Cosmos patched. |
| S186 | UI bugs, stale closures, and email footer missing | **Bug fix + email refactor** — button color, auto-save stale closure, avatar 413, unsubscribe footer via `format_branded_email()` refactor (12 modules). AI-generated widget greeting. v1.88.0. |
| S187 | Specs claim "implemented" but code doesn't match | **Full spec-vs-code verification** — all 2,009 specs verified against source. 3 mismatches found, 369 weak assertions, 7 missing specs created (SPEC-1806–1812). v1.88.1. |
| S188 | 91 specs stuck in "specified" status | **Specified-spec triage** — 16 promoted to implemented, 7 retired, 7 WIs created for genuine gaps. Transport hierarchy clarified (SLIM required, NATS fallback, HTTP external-only). |
| S189 | Repeatable procedures exist only as prose in KB; no executable enforcement | **Claude Code Skills** — 8 project-level skills wrapping deployment, testing, tenant seeding, and KB management workflows. Skills mechanize GOV-01/GOV-12/GOV-13 governance chains. SCHEDULE.md and CLAUDE.md wrap-up procedures refactored to delegate to skills. |

### Current Database (as of Session 189)

| Metric | Count |
|--------|-------|
| Specifications | 2,016 (313 verified, 1,448 implemented, 68 specified, 187 retired) |
| Test artifacts | 20,248 (linked to specifications) |
| Work items | 1,385 (1,371 resolved/closed, 14 open) |
| Machine-verifiable assertions | 100% pass rate across all assertable specs |
| Knowledge documents | 175 |
| Operational procedures | 17 |
| Governance principles | 21 (GOV-01 through GOV-18 + 3 architectural) |
| Test plan phases | 13 active, 3 removed (live-only per SPEC-1649) |
| Testable elements | 520 (UI component inventory for coverage tracking) |
| Live E2E tests | 936 (across 3 admin consoles: Standalone 576, Provider 264, Shopify 96) |
| Mock E2E tests | 527 (zero-backend UI testing across 14 test files) |
| Backlog snapshots | 16 |
| Automated tests passing | 6,053 (unit + multi-tenant + agents + integrations) |
| Claude Code skills | 8 (deployment, testing, seeding, KB management) |
| Data loss incidents | 0 |

### What the System Catches

- **Regressions at session start** — assertions run automatically before work begins, flagging any spec whose implementation has drifted
- **Phantom artifact references** — the database enforces that every referenced concept has backing storage and change control
- **Specification drift** — append-only versioning preserves the full decision history; nothing is silently overwritten
- **Cold-start amnesia** — session handoff prompts give each new session the context it needs without human re-explanation
- **Accumulated process drift** — every 5th session is an audit, catching errors that compound across sessions
- **Untested specifications** — `get_untested_specs()` identifies coverage gaps on demand

## Skills — Executable Governance

As of Session 189, the Membase pattern extends beyond the database and hooks into **Claude Code skills** — SKILL.md files that encode repeatable workflows as executable procedures.

### The Problem Skills Solve

Governance rules (GOV-01 through GOV-18) tell Claude *what to do*, but enforcement relied on Claude's self-discipline and hook reminders. Multi-step chains like "create work item → create linked test → assign to test plan phase → add to backlog" (GOV-12 + GOV-13) were easy to partially execute, silently dropping steps.

### The Solution

Skills turn prose procedures into step-by-step executable playbooks. Claude Code loads them on demand, and each skill contains the exact Python/bash commands to complete the workflow. Two invocation modes prevent accidents:

- **Owner-only** (`disable-model-invocation: true`) — for destructive operations (deploy, seed, session wrap-up). Claude cannot trigger these autonomously.
- **Auto-invocable** — for knowledge work (KB queries, spec creation, test linking). Claude uses these proactively when the conversation warrants it.

### Reference Implementation: 8 Project Skills

| Skill | Invocation | Purpose |
|-------|-----------|---------|
| `/deploy` | Owner only | Full build-deploy-verify pipeline with GOV-16 deploy gate |
| `/seed-tenant` | Owner only | 9-phase Cosmos DB tenant provisioning |
| `/kb-session-wrap` | Owner only | 5-phase structured session wrap-up |
| `/run-tests` | Owner + Claude | Thermal-safe batch runner + PLAN-001 E2E pipeline |
| `/kb-query` | Owner + Claude | Read-only Knowledge Database lookups |
| `/kb-spec` | Owner + Claude | Guided spec creation with duplicate detection (GOV-01) |
| `/kb-work-item` | Owner + Claude | WI → Test → Phase assignment chain (GOV-12 + GOV-13) |
| `/kb-promote` | Owner + Claude | Assertion-gated spec status promotion |

### Skill File Structure

```
.claude/skills/
  deploy/
    SKILL.md          # YAML frontmatter + markdown instructions
  kb-query/
    SKILL.md
  kb-work-item/
    SKILL.md
  ...
```

Each `SKILL.md` contains YAML frontmatter (name, description, invocation control, allowed tools) followed by markdown instructions with embedded code blocks. Skills follow the [Agent Skills](https://agentskills.io) open standard.

### Key Design Principle

**CLAUDE.md states the rule, skills encode the execution, KB procedures are the audit trail.** This three-layer separation means rules don't need to contain implementation details, skills don't need to repeat governance rationale, and KB procedures remain the canonical historical record.

## Why Not Just Use Markdown?

The markdown-only approach (CLAUDE.md + MEMORY.md + topic files) works well for the first ~20 sessions. After that:

- Files grow unwieldy and contradictions accumulate
- There's no machine-verifiable way to know if what Claude "remembers" is still true
- MEMORY.md isn't version-controlled — there's no change history
- Claude can't partially load a document, so everything gets loaded every time
- Context window compaction makes drift worse, not better
- Claude silently "drifts," dropping memories and skipping procedures

Membase solves this by adding a structured layer with change control, versioned history, and automated verification — while keeping the markdown files for what they're good at (rules, preferences, operational patterns).

## Background

This pattern was developed incrementally on the [Agent Red Customer Experience](https://agentredcx.com) project by Remaker Digital. Working with an engineering team of one, the full weight of Agile and formal project management tools was unnecessary. What was needed was a shared, persistent, change-controlled memory between a human and an AI engineering partner.

The database is used exclusively by Claude and contains only what Claude needs to remember. The human observes through a lightweight read-only UI (sort, filter, search, tree-view, change history) that deliberately excludes write operations. When the human spots a discrepancy, they tell Claude, and Claude creates a corrected version.

The current database contains 2,016 specifications, 20,248 test artifacts, 1 test plan (13 active phases, 3 removed), 1,385 work items (14 open), 17 operational procedures, 175 documents, 520 testable elements, and machine-verifiable assertions at 100% pass rate — all accumulated across 189 sessions with zero data loss. Session 189 introduced 8 Claude Code skills that mechanize governance workflows as executable playbooks.

---

*The implementation approach is freely reusable under the MIT license. Adapt the schema to your project's needs — the core principles (append-only, machine-verifiable assertions, live-only test verification, quality dashboard, governance discipline, session handoff, audit cadence) are universal.*

*© 2026 Remaker Digital, a DBA of VanDusen & Palmeter, LLC. All rights reserved.*
