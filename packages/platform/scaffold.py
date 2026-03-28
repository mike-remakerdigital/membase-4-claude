from __future__ import annotations

from pathlib import Path

TEMPLATES: dict[str, str] = {
    "CLAUDE.md": """# CLAUDE.md

This project was initialized by GroundTruth for a three-party operating model.

Compatibility note: the platform still uses the `membase` CLI and
`membase.project.json` manifest during the transition period.

- Prime Builder: proposes and implements approved changes
- Loyal Opposition: challenges proposals and implementations with evidence
- Human AI Engineer: resolves disagreement, accepts risk, and sets priority

## Governing Files

- `membase.project.json` is the project manifest
- `memory/MEMORY.md` stores durable operating notes
- `memory/handoffs/` stores next-session prompts and session wrap artifacts
- `docs/evidence/` stores observed runtime evidence and contradiction records
- `docs/bridge/` stores bridge contracts and agent-to-agent coordination notes
- `tools/knowledge-db/` is the managed knowledge base runtime

## Required Workflow

1. Run the Stage 0 artifact sweep before proposing changes
2. Record or update specifications before implementation
3. Derive or update tests from the governing specifications
4. Implement only after proposal challenge is resolved
5. Capture observed reality when runtime behavior disagrees with source artifacts
6. Leave a handoff in `memory/handoffs/` before ending the session

## Managed Platform Assets

- `.claude/hooks/assertion-check.py`
- `.claude/hooks/spec-classifier.py`
- `.claude/rules/`
- `tools/knowledge-db/`

Do not overwrite project-owned product code with platform changes without explicit review.
""",
    ".gitignore": """__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/
.venv/
venv/
.DS_Store
Thumbs.db
""",
    "README.md": """# __PROJECT_NAME__

Initialized by GroundTruth.

Compatibility note: bootstrap commands still use the `membase` CLI during the
transition period.

## Operating Model

This scaffold assumes a three-party development system:

- Prime Builder implements approved work
- Loyal Opposition reviews proposals and completed changes
- The human operator resolves disagreements and accepts residual risk

The project is organized around three artifact classes plus one runtime evidence surface:

- specifications
- tests
- system artifacts
- observed reality

## First Run

1. `membase kb seed --path .`
2. `membase kb verify --path .`
3. `membase kb serve --path .`
4. Read `docs/runbooks/bootstrap-checklist.md`
5. Configure your bridge transport in `.mcp.project.json`

## Key Paths

- Manifest: `membase.project.json`
- Session memory: `memory/MEMORY.md`
- Session handoffs: `memory/handoffs/`
- Specs: `docs/specs/`
- Tests: `docs/tests/`
- Evidence: `docs/evidence/`
""",
    "QUICKSTART.md": """# __PROJECT_NAME__ Quickstart

## Bootstrap

1. Run `membase kb seed --path .`
2. Run `membase kb verify --path .`
3. Run `membase kb serve --path .`
4. Review `.claude/rules/transaction-protocol.md`
5. Configure your bridge transport in `.mcp.project.json`

## Before The First Implementation Session

1. Read `docs/runbooks/bootstrap-checklist.md`
2. Create or confirm the first governing specifications in `docs/specs/`
3. Create or confirm the first derived tests in `docs/tests/`
4. Verify `memory/handoffs/NEXT_SESSION_TEMPLATE.md` fits your session-wrap process

## First Review Loop

1. Prime Builder writes a proposal
2. Loyal Opposition challenges the proposal
3. Prime Builder implements
4. Loyal Opposition reviews the implementation and recommends go/no-go
""",
    ".claude/settings.project.json": """{
  "$schema": "https://raw.githubusercontent.com/anthropics/claude-code/main/.claude/settings.schema.json",
  "hooks": {
    "SessionStart": [
      {
        "type": "command",
        "command": "python .claude/hooks/assertion-check.py",
        "timeout": 30000
      }
    ],
    "UserPromptSubmit": [
      {
        "type": "command",
        "command": "python .claude/hooks/spec-classifier.py",
        "timeout": 5000
      }
    ]
  }
}
""",
    ".mcp.project.json": """{
  "mcpServers": {}
}
""",
    ".claude/rules/prime-builder-operating-contract.md": """# Prime Builder Operating Contract

Prime Builder is the implementation role.

Responsibilities:

- propose changes with explicit scope and governing artifacts
- implement only after proposal challenge is resolved
- keep changes within approved scope
- record what changed and how it was verified

Prime Builder does not self-approve release risk. Go/no-go belongs to Loyal Opposition plus the human operator.
""",
    ".claude/rules/loyal-opposition-operating-contract.md": """# Loyal Opposition Operating Contract

Loyal Opposition is the challenge and review role.

Responsibilities:

- challenge proposal scope, assumptions, and missing evidence
- compare implementation against governing specs, tests, and observed reality
- report findings with severity and explicit evidence
- recommend go/no-go for commit or push

Loyal Opposition should not silently expand scope and should not implement changes unless the human operator explicitly reassigns that work.
""",
    ".claude/rules/transaction-protocol.md": """# Transaction Protocol

This project uses a five-stage builder/opposition protocol.

## Stage 0: Pre-Proposal Artifact Sweep

- identify relevant specs, tests, prior reviews, ADRs, and runbooks
- surface conflicts before new proposal work starts

## Stage 1: Proposal

- Prime Builder proposes the change
- proposal lists scope, governing artifacts, risks, and intended verification

## Stage 2: Proposal Challenge

- Loyal Opposition reviews the proposal
- challenge focuses on omissions, drift, and insufficient evidence

## Stage 3: Implementation

- Prime Builder implements only the approved scope
- implementation output records changed files and verification results

## Stage 4: Implementation Challenge / Go-No-Go

- Loyal Opposition reviews the completed change
- recommendation must state findings, residual risk, and go/no-go

The human operator adjudicates unresolved disagreement.
""",
    ".claude/rules/stage-0-artifact-sweep.md": """# Stage 0 Artifact Sweep

Before new proposal work begins, check:

- specifications
- derived tests
- runbooks and prior reviews
- current implementation state
- observed runtime evidence if behavior is disputed

If an existing artifact already governs the decision, proposals must start from that baseline rather than re-inventing it from memory.
""",
    ".claude/rules/session-handoff.md": """# Session Handoff Contract

Every substantial session should leave a handoff artifact under `memory/handoffs/`.

A good handoff includes:

- what changed
- what remains open
- what evidence was produced
- what risks or blockers remain
- the first recommended action for the next session

The knowledge base stores structured session prompts. The handoff directory provides human-readable continuity across session boundaries.
""",
    ".claude/hooks/assertion-check.py": """#!/usr/bin/env python3
\"\"\"
SessionStart hook for Membase-generated projects.

Responsibilities:
1. run KB assertions
2. warn when the git worktree is dirty
3. inject the latest unconsumed session handoff prompt
\"\"\"

import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()))
KB_DIR = PROJECT_DIR / "__KB_ROOT__"


def _run_assertions(db) -> list[str]:
    try:
        from assertions import run_all_assertions

        summary = run_all_assertions(db, triggered_by="session-start")
        passed = summary.get("passed", 0)
        failed = summary.get("failed", 0)
        total = summary.get("specs_with_assertions", 0)
        lines = [f"Assertion check: {passed}/{total} PASS, {failed} FAIL"]

        failures = [
            detail
            for detail in summary.get("details", [])
            if not detail.get("skipped") and not detail["overall_passed"]
        ]
        if failures:
            lines.append("Failing specifications:")
            for detail in failures:
                lines.append(f"  [{detail['spec_id']}] {detail['title']}")
        return lines
    except Exception as exc:
        return [f"Assertion check error: {exc}"]


def _check_git_clean() -> list[str]:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(PROJECT_DIR),
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return [f"Git status check failed: {(result.stderr or result.stdout).strip()}"]
        if not result.stdout.strip():
            return []

        lines = ["WORKTREE DIRTY:"]
        for line in result.stdout.splitlines():
            lines.append(f"  {line}")
        return lines
    except Exception as exc:
        return [f"Git status check error: {exc}"]


def _read_handoff_prompt(db) -> list[str]:
    try:
        prompt = db.get_next_session_prompt()
        if not prompt:
            return []

        lines = [
            "",
            "=" * 50,
            f"SESSION HANDOFF from {prompt['session_id']}",
            "=" * 50,
            prompt["prompt_text"],
            "=" * 50,
        ]
        db.consume_session_prompt(prompt["session_id"])
        return lines
    except Exception as exc:
        return [f"Session handoff read error: {exc}"]


def main() -> None:
    try:
        json.loads(sys.stdin.read())
    except Exception:
        pass

    db_path = KB_DIR / "knowledge.db"
    if not db_path.exists():
        json.dump({}, sys.stdout)
        sys.exit(0)

    sys.path.insert(0, str(KB_DIR))
    try:
        from db import KnowledgeDB

        db = KnowledgeDB(str(db_path))
        try:
            lines = _run_assertions(db)
            lines.extend(_check_git_clean())
            lines.extend(_read_handoff_prompt(db))
        finally:
            db.close()

        json.dump({"additionalContext": "\\n".join(lines)}, sys.stdout)
    except Exception as exc:
        json.dump({"additionalContext": f"SessionStart hook error: {exc}"}, sys.stdout)

    sys.exit(0)


if __name__ == "__main__":
    main()
""",
    ".claude/hooks/spec-classifier.py": """#!/usr/bin/env python3
\"\"\"
UserPromptSubmit hook for Membase-generated projects.

Detects specification-like language and reminds the AI to follow the
specification-first workflow before implementation.
\"\"\"

import json
import re
import sys

SPEC_PATTERNS = [
    r"\\bmust\\s+(include|have|support|provide|implement|ensure|validate|contain)\\b",
    r"\\bshould\\s+(include|have|support|provide|implement|ensure|validate|contain)\\b",
    r"\\bshall\\s+(include|have|support|provide|implement|ensure|validate|contain)\\b",
    r"\\bneeds?\\s+to\\s+(include|have|support|provide|implement|ensure|validate|contain)\\b",
    r"(?:^|\\n)\\s*\\d+\\.\\s+\\w.+(?:\\n\\s*\\d+\\.\\s+\\w.+){2,}",
    r"\\bthe\\s+(?:system|product|feature|workflow|service|ui|api)\\s+(?:must|shall|should)\\b",
]

ANTI_PATTERNS = [
    r"^(?:stop|wait|pause|hold|cancel)\\b",
    r"^(?:what|how|why|where|when|who|can you|do you|is there|are there)\\b",
    r"^(?:show|list|read|open|check|look|find|search|grep|run|execute)\\b",
]

REMINDER = \"\"\"SPECIFICATION CLASSIFIER TRIGGER

The owner's message appears to contain specification-like language.
Before implementation:

1. Run the Stage 0 artifact sweep
2. Record or verify governing specifications
3. Create or verify derived tests
4. Present the proposal and gaps for challenge
5. Wait for explicit approval before implementation
\"\"\"


def detect_specification_language(prompt: str) -> bool:
    stripped = prompt.strip()
    if len(stripped) < 40:
        return False

    first_line = stripped.split("\\n")[0].strip().lower()
    for pattern in ANTI_PATTERNS:
        if re.search(pattern, first_line, re.IGNORECASE):
            return False

    for pattern in SPEC_PATTERNS:
        if re.search(pattern, stripped, re.IGNORECASE | re.MULTILINE):
            return True

    return False


def main() -> None:
    try:
        data = json.loads(sys.stdin.read())
        prompt = data.get("user_prompt", "")
        if detect_specification_language(prompt):
            json.dump({"systemMessage": REMINDER}, sys.stdout)
        else:
            json.dump({}, sys.stdout)
    except Exception:
        json.dump({}, sys.stdout)


if __name__ == "__main__":
    main()
""",
    "docs/specs/README.md": """# Specifications

Store governing specifications here.

Guidelines:

- specifications are append-oriented and change-controlled
- they describe intended behavior from the perspective of users, operators, maintainers, or administrators
- implementation should not start until the governing specification baseline is clear

Use the Stage 0 artifact sweep before adding or changing specs.
""",
    "docs/tests/README.md": """# Tests

Store derived tests and test plans here.

Guidelines:

- tests are derived from governing specifications
- tests should verify production-relevant behavior, not only implementation trivia
- when runtime behavior conflicts with source artifacts, record observed reality in `docs/evidence/`
""",
    "docs/evidence/README.md": """# Observed Reality

This directory stores runtime-derived evidence used to break ties when source artifacts disagree.

Examples:

- logs
- traces
- screenshots
- deployment-state captures
- recorded failures

Observed reality is an evidence surface, not an authored source-of-truth artifact.
""",
    "docs/bridge/README.md": """# Bridge Contract

If this project uses Prime Builder + Loyal Opposition, configure a structured bridge transport.

Minimum message fields:

- subject
- body
- priority
- correlation id
- artifact references
- expected response

The bridge should carry proposals, findings, status updates, and go/no-go recommendations without relying on shared chat context alone.
""",
    "docs/runbooks/bootstrap-checklist.md": """# Bootstrap Checklist

1. Run `membase doctor`
2. Run `membase kb seed --path .`
3. Run `membase kb verify --path .`
4. Review `.claude/rules/`
5. Configure your bridge transport in `.mcp.project.json`
6. Confirm the first specifications in `docs/specs/`
7. Confirm the first derived tests in `docs/tests/`
8. Confirm the session handoff workflow in `memory/handoffs/`
""",
    "docs/runbooks/session-wrap.md": """# Session Wrap Runbook

Before ending a substantial session:

1. summarize what changed
2. record unresolved risks and blockers
3. capture runtime evidence if behavior was disputed
4. leave the next-session prompt in `memory/handoffs/`
5. ensure the KB and source files agree on the current state
""",
    "memory/MEMORY.md": """# MEMORY.md

Store durable operating notes here.

Use this file for:

- decisions about how the team works
- tool-specific caveats
- recurring project preferences

Do not treat this file as the only source of truth for specifications or tests.
""",
    "memory/handoffs/README.md": """# Session Handoffs

Leave a handoff artifact here at the end of each substantial session.

The handoff should answer:

- what changed
- what remains open
- what evidence was collected
- what the next session should do first
""",
    "memory/handoffs/NEXT_SESSION_TEMPLATE.md": """# Next Session Handoff

## What Changed

- 

## Governing Artifacts

- 

## Evidence Produced

- 

## Open Risks / Blockers

- 

## Recommended First Action

- 
""",
}


def _render_template(content: str, replacements: dict[str, str]) -> str:
    rendered = content
    for key, value in replacements.items():
        rendered = rendered.replace(key, value)
    return rendered


def install_project_scaffold(
    project_root: str | Path,
    *,
    project_name: str,
    slug: str,
    kb_root: str,
    kb_db_path: str,
    force: bool = False,
) -> list[Path]:
    root = Path(project_root).resolve()
    replacements = {
        "__PROJECT_NAME__": project_name,
        "__PROJECT_SLUG__": slug,
        "__KB_ROOT__": kb_root.replace("\\", "/"),
        "__KB_DB_PATH__": kb_db_path.replace("\\", "/"),
    }

    copied: list[Path] = []
    for relative_path, content in TEMPLATES.items():
        target_path = root / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if target_path.exists() and not force:
            continue
        rendered = _render_template(content, replacements)
        target_path.write_text(rendered, encoding="utf-8")
        copied.append(target_path)

    return copied
