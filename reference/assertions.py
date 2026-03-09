"""
Membase Assertion Runner — reads assertion definitions from the knowledge database,
executes grep/glob checks against the local codebase, and writes results back.

Three assertion types:
  - grep:        re.findall(pattern, file_content) count >= min_count
  - glob:        Path.glob(pattern) returns >= 1 match
  - grep_absent: re.findall(pattern, file_content) count == 0

Usage:
  python reference/assertions.py                  # run all, manual trigger
  python reference/assertions.py --pre-build      # pre-build gate
  python reference/assertions.py --session-start  # session startup check
  python reference/assertions.py --spec SPEC-001  # single spec only

MIT License — see LICENSE for details.
"""

from __future__ import annotations

import argparse
import io
import os
import re
import sys
from pathlib import Path
from typing import Any

# Windows cp1252 stdout encoding fix
if __name__ == "__main__":
    if sys.stdout and hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if sys.stderr and hasattr(sys.stderr, "buffer"):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Project root: use MEMBASE_PROJECT_ROOT env var, or fall back to cwd
PROJECT_ROOT = Path(os.environ.get("MEMBASE_PROJECT_ROOT", os.getcwd())).resolve()

# Import sibling module
sys.path.insert(0, str(Path(__file__).parent))
from db import KnowledgeDB


_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB — skip binary/huge files


def _read_file_safe(file_path: Path) -> str | None:
    """Read file contents, returning None if file doesn't exist or can't be read."""
    try:
        if file_path.stat().st_size > _MAX_FILE_SIZE:
            return None
        return file_path.read_text(encoding="utf-8", errors="replace")
    except (OSError, PermissionError):
        return None


_VALID_ASSERTION_TYPES = {"grep", "glob", "grep_absent"}


def run_single_assertion(assertion: dict[str, Any]) -> dict[str, Any]:
    """Execute one assertion definition and return the result.

    Each assertion dict has:
      - type: "grep", "glob", or "grep_absent"
      - pattern: regex pattern (grep/grep_absent) or glob pattern (glob)
      - file: relative file path from project root (grep/grep_absent)
      - min_count: minimum match count (grep only, default 1)
      - description: human-readable explanation
      - contains: (glob only) optional string that must appear in matched files

    Returns: {type, description, passed, detail}
    """
    a_type = assertion.get("type", "")
    pattern = assertion.get("pattern") or assertion.get("query", "")
    description = assertion.get("description", "") or f"{a_type}: {pattern}"

    # Skip non-machine types gracefully
    if a_type not in _VALID_ASSERTION_TYPES:
        return {
            "type": a_type, "description": description, "passed": True,
            "detail": f"Skipped non-machine assertion type: {a_type!r}",
            "skipped": True,
        }
    if not pattern:
        return {
            "type": a_type, "description": description, "passed": False,
            "detail": f"Missing 'pattern' for assertion type '{a_type}'",
        }

    result: dict[str, Any] = {
        "type": a_type, "description": description, "passed": False, "detail": "",
    }

    if a_type == "grep":
        file_field = (assertion.get("file") or assertion.get("file_pattern")
                      or assertion.get("target") or assertion.get("path")
                      or assertion.get("expected") or "")
        if not file_field:
            result["detail"] = "Missing 'file' field for grep assertion"
            return result

        # Expand glob patterns in file field
        if "*" in file_field or "?" in file_field:
            matches = list(PROJECT_ROOT.glob(file_field))
            if not matches:
                result["detail"] = f"No files matching glob '{file_field}'"
                return result
            file_paths = matches
        else:
            file_paths = [PROJECT_ROOT / file_field]

        min_count = assertion.get("min_count", 1)
        total_matches = 0
        for fp in file_paths:
            content = _read_file_safe(fp)
            if content is None:
                continue
            total_matches += len(re.findall(pattern, content))

        result["passed"] = total_matches >= min_count
        result["detail"] = (
            f"Found {total_matches} match(es) for /{pattern}/ "
            f"(need >= {min_count}) in {file_field}"
        )

    elif a_type == "glob":
        matches = list(PROJECT_ROOT.glob(pattern))
        contains = assertion.get("contains")
        if contains and matches:
            matches = [m for m in matches if contains in (_read_file_safe(m) or "")]
        result["passed"] = len(matches) > 0
        result["detail"] = (
            f"Glob '{pattern}' matched {len(matches)} file(s)"
            + (f" containing '{contains}'" if contains else "")
        )

    elif a_type == "grep_absent":
        file_field = (assertion.get("file") or assertion.get("file_pattern")
                      or assertion.get("target") or assertion.get("path") or "")
        if not file_field:
            result["detail"] = "Missing 'file' field for grep_absent assertion"
            return result

        fp = PROJECT_ROOT / file_field
        content = _read_file_safe(fp)
        if content is None:
            result["passed"] = True
            result["detail"] = f"File '{file_field}' not found (pattern absent by default)"
        else:
            count = len(re.findall(pattern, content))
            result["passed"] = count == 0
            result["detail"] = f"Found {count} match(es) for /{pattern}/ in {file_field}"

    return result


def run_spec_assertions(
    db: KnowledgeDB, spec: dict[str, Any], triggered_by: str
) -> dict[str, Any]:
    """Run all assertions for one spec, record results in DB, return summary."""
    spec_id = spec["id"]
    spec_version = spec["version"]
    assertions = spec.get("_assertions_parsed") or []

    if not assertions:
        return {
            "spec_id": spec_id, "title": spec["title"],
            "overall_passed": True, "results": [], "assertion_count": 0,
            "skipped": True,
        }

    results = [run_single_assertion(a) for a in assertions]

    # Only machine-checkable assertions determine overall_passed
    machine_results = [r for r in results if not r.get("skipped")]
    if machine_results:
        overall_passed = all(r["passed"] for r in machine_results)
    else:
        overall_passed = True

    db.insert_assertion_run(
        spec_id=spec_id, spec_version=spec_version,
        overall_passed=overall_passed, results=results,
        triggered_by=triggered_by,
    )

    return {
        "spec_id": spec_id, "title": spec["title"],
        "overall_passed": overall_passed, "results": results,
        "assertion_count": len(machine_results),
        "skipped": len(machine_results) == 0 and len(results) > 0,
    }


def run_all_assertions(
    db: KnowledgeDB, triggered_by: str = "manual", spec_id: str | None = None
) -> dict[str, Any]:
    """Run assertions for all specs (or a single spec) and return summary."""
    if spec_id:
        spec = db.get_spec(spec_id)
        if not spec:
            return {"error": f"Spec {spec_id} not found"}
        specs = [spec]
    else:
        specs = db.list_specs()

    details = []
    passed = failed = skipped = 0

    for spec in specs:
        result = run_spec_assertions(db, spec, triggered_by)
        details.append(result)
        if result.get("skipped"):
            skipped += 1
        elif result["overall_passed"]:
            passed += 1
        else:
            failed += 1

    return {
        "total_specs": len(specs),
        "specs_with_assertions": len(specs) - skipped,
        "passed": passed, "failed": failed, "skipped": skipped,
        "triggered_by": triggered_by, "details": details,
    }


def print_summary(summary: dict[str, Any]) -> None:
    """Print a human-readable assertion summary to stdout."""
    if "error" in summary:
        print(f"ERROR: {summary['error']}")
        return

    print(f"\n{'=' * 60}")
    print(f"  Assertion Results -- triggered by: {summary['triggered_by']}")
    print(f"{'=' * 60}")
    print(f"  Total specs:       {summary['total_specs']}")
    print(f"  With assertions:   {summary['specs_with_assertions']}")
    print(f"  PASSED:            {summary['passed']}")
    print(f"  FAILED:            {summary['failed']}")
    print(f"  Skipped (no def):  {summary['skipped']}")
    print(f"{'=' * 60}\n")

    failures = [d for d in summary["details"] if not d.get("skipped") and not d["overall_passed"]]
    if failures:
        print("FAILURES:\n")
        for f in failures:
            print(f"  [{f['spec_id']}] {f['title']}")
            for r in f["results"]:
                status = "PASS" if r["passed"] else "FAIL"
                print(f"    [{status}] {r['description']}: {r['detail']}")
            print()

    passes = [d for d in summary["details"] if not d.get("skipped") and d["overall_passed"]]
    if passes:
        print("PASSED:\n")
        for p in passes:
            print(f"  [{p['spec_id']}] {p['title']} ({p['assertion_count']} assertions)")
        print()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run assertions against codebase")
    parser.add_argument("--pre-build", action="store_true", help="Pre-build gate mode")
    parser.add_argument("--session-start", action="store_true", help="Session startup check")
    parser.add_argument("--spec", type=str, default=None, help="Single spec ID")
    args = parser.parse_args()

    triggered_by = "manual"
    if args.pre_build:
        triggered_by = "pre-build"
    elif args.session_start:
        triggered_by = "session-start"

    db = KnowledgeDB()
    try:
        summary = run_all_assertions(db, triggered_by=triggered_by, spec_id=args.spec)
        print_summary(summary)
        return 1 if summary.get("failed", 0) > 0 else 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
