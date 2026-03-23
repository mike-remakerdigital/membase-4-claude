---
name: kb-session-wrap
description: Execute the structured 5-phase session wrap-up procedure. Updates KB, MEMORY.md, pushes to git, and generates handoff prompt for the next session.
disable-model-invocation: true
argument-hint: [session-id]
allowed-tools: Bash, Read, Write, Edit, Grep, Glob
metadata:
  category: session-management
  owner-only: true
---

# Session Wrap-Up

Execute the complete 5-phase session wrap-up procedure.

**Arguments:** `$ARGUMENTS[0]` = session ID (e.g., `S42`). If omitted, derive from MEMORY.md Recent Sessions (increment highest by 1).

## Phase 1: Knowledge Database Updates

### 1.1 Spec Status Updates
Review all work done this session. For each spec implemented or verified, promote using assertion validation:

```python
import sys; sys.path.insert(0, 'tools/knowledge-db')
from db import KnowledgeDB
kb = KnowledgeDB()

# For each spec completed this session:
kb.update_spec(id="SPEC-XXXX", status="implemented",
    changed_by="claude", change_reason="Implemented in session SXXX")
```

### 1.2 Run Assertions
```bash
python .claude/hooks/assertion-check.py
```
- **New failures** (previously passing) = regressions -> create work items
- **Existing failures** (already tracked) = expected -> no action

### 1.3 Close Resolved Work Items
Review all open WIs. For each resolved this session:
```python
kb.update_work_item(id="WI-XXXX", stage="resolved",
    changed_by="claude", change_reason="Resolved in session SXXX")
```

## Phase 2: Memory & Documentation Updates

### 2.1 Update MEMORY.md
1. **Current Status** -- version numbers, test counts, deployment info
2. **Recent Sessions** -- add `- SXXX: **Bold summary.** Details.`
3. **Quick Reference** -- update any changed values (versions, URLs, counts)

### 2.2 Update CLAUDE.md (if needed)
Only if new rules, governance principles, or procedures were established. This should be rare.

### 2.3 Verify Procedures
Check that all referenced operational procedures are still accurate.

### 2.4 Confirm Regression Tests
For each bug fix, verify a regression test exists in KB.

## Phase 3: External Updates

### 3.1 Git Commit & Push
```bash
git add -A && git status
# Review staged changes -- exclude sensitive files
git commit -m "SXXX: <summary of session work>"
git push origin main
```

### 3.2 Documentation Site (if applicable)
If customer-visible features changed, update and deploy docs.

## Phase 4: Deployment Risk Gate

Assess deployment readiness:
- [ ] Tests passing?
- [ ] Assertions intact (no regressions)?
- [ ] Changes backward-compatible?
- [ ] All work items resolved?

If ANY fails, skip deployment and record reason. Otherwise deploy via `/deploy`.

## Phase 5: Handoff Prompt

Generate the next-session handoff prompt and store it:

```python
kb.insert_session_prompt("SXXX",
    prompt_text="Continue work on [project]. Session SXXX completed: [summary]. "
        "Next priorities: [WI-XXXX, WI-YYYY]. "
        "[N] tests passing, [M] failures.",
    context={
        "version": "X.Y.Z",
        "test_count": NNNN,
        "next_tasks": ["WI-XXXX", "WI-YYYY"],
    })
```

Clean up temporary/scratch files. Verify no stale env changes committed.

## Audit Session Check

Every 5th session (S5, S10, S15, ...) requires extra steps:
- Fresh-context assertion review (run all, not just changed)
- MEMORY.md accuracy check against actual codebase state
- Procedure verification (are all documented procedures still accurate?)
- Stale work item triage (close or update long-open items)

## Completion Checklist

```
Session Wrap-Up: SXXX
-----------------------------------
[ ] Phase 1: KB specs promoted, assertions run, WIs closed
[ ] Phase 2: MEMORY.md updated, procedures verified
[ ] Phase 3: Git pushed, docs updated (if needed)
[ ] Phase 4: Deployment assessed (or skip reason recorded)
[ ] Phase 5: Handoff prompt generated, temp files cleaned
-----------------------------------
```
