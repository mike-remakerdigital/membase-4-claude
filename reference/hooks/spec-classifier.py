#!/usr/bin/env python3
"""
Membase Reference — UserPromptSubmit Hook (Spec Classifier)

Detects owner input that contains specification-like language (requirements,
business rules, "must/should/shall" directives) and injects a system message
reminding the AI to follow the specification-first workflow:

  1. Record or verify specifications in KB
  2. Create work items for gaps
  3. Present work items for prioritization
  4. Only then proceed to implementation

This is a mechanical guardrail — it fires BEFORE the AI sees the message,
ensuring the classification step cannot be skipped.

Stdin:  JSON {"user_prompt": "...", "session_id": "...", ...}
Stdout: JSON {"systemMessage": "..."} or {}
Exit:   Always 0

MIT License — see LICENSE for details.
"""

import json
import re
import sys


# ── Detection patterns ──

SPEC_PATTERNS = [
    # Modal verbs indicating requirements
    r"\bmust\s+(include|have|support|provide|implement|ensure|validate|contain)\b",
    r"\bshould\s+(include|have|support|provide|implement|ensure|validate|contain)\b",
    r"\bshall\s+(include|have|support|provide|implement|ensure|validate|contain)\b",
    r"\bneeds?\s+to\s+(include|have|support|provide|implement|ensure|validate|contain)\b",
    # Numbered requirements lists
    r"(?:^|\n)\s*\d+\.\s+\w.+(?:\n\s*\d+\.\s+\w.+){2,}",
    # Explicit requirement language
    r"\brequire(?:ment|d|s)?\b.*\b(?:must|shall|should)\b",
    r"\bthe\s+(?:system|product|feature|test|widget|api|ui)\s+(?:must|shall|should)\b",
    # Business decision language
    r"\bwe\s+(?:need|want|require)\s+(?:it|the|this|our)\b",
    r"\bfrom\s+now\s+on\b",
    r"\balways\s+(?:use|do|require|include|ensure)\b",
    r"\bnever\s+(?:use|do|allow|skip|omit)\b",
]

ANTI_PATTERNS = [
    r"^(?:stop|wait|pause|hold|cancel)\b",
    r"^(?:what|how|why|where|when|who|can you|do you|is there|are there)\b",
    r"^(?:show|list|read|open|check|look|find|search|grep|run|execute|deploy|commit)\b",
    r"^(?:fix|debug|investigate|explain|describe|summarize)\b",
    r"^(?:yes|no|ok|sure|agreed|approved|proceed|continue|go ahead)\b",
]

MIN_SPEC_LENGTH = 40


def detect_specification_language(prompt: str) -> bool:
    """Return True if the prompt likely contains specification language."""
    stripped = prompt.strip()
    if len(stripped) < MIN_SPEC_LENGTH:
        return False

    first_line = stripped.split("\n")[0].strip().lower()
    for pattern in ANTI_PATTERNS:
        if re.search(pattern, first_line, re.IGNORECASE):
            return False

    for pattern in SPEC_PATTERNS:
        if re.search(pattern, stripped, re.IGNORECASE | re.MULTILINE):
            return True

    return False


REMINDER = """SPECIFICATION CLASSIFIER TRIGGER -- The owner's message appears to contain specification-like language (requirements, "must include", numbered criteria). Before writing any code:

1. Classify the owner's statements as specifications (new or updates to existing).
2. Record specifications in the Knowledge Database via db.insert_spec().
3. Create work items for any gap between current state and the specifications.
4. Present the work items to the owner for prioritization.
5. Wait for explicit prioritization approval before implementing.

Specification-first workflow: always record the requirement BEFORE implementing it."""


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
