"""
Membase assertion runner.

Reads assertion definitions from the knowledge database, executes grep and glob
checks against the local codebase, and writes results back into the database.
"""

from __future__ import annotations

import argparse
import io
import os
import re
import sys
from pathlib import Path
from typing import Any

if __name__ == "__main__":
    if sys.stdout and hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if sys.stderr and hasattr(sys.stderr, "buffer"):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

try:
    from .db import KnowledgeDB
except ImportError:  # pragma: no cover - used by copied project runtime
    from db import KnowledgeDB

DEFAULT_PROJECT_ROOT = Path(
    os.environ.get(
        "MEMBASE_PROJECT_ROOT",
        Path(__file__).resolve().parent.parent.parent,
    )
).resolve()
DEFAULT_DB_PATH = Path(
    os.environ.get("MEMBASE_KB_DB", Path(__file__).resolve().parent / "knowledge.db")
).resolve()

_MAX_FILE_SIZE = 10 * 1024 * 1024
_VALID_ASSERTION_TYPES = {"grep", "glob", "grep_absent"}


def _read_file_safe(file_path: Path) -> str | None:
    try:
        if file_path.stat().st_size > _MAX_FILE_SIZE:
            return None
        return file_path.read_text(encoding="utf-8", errors="replace")
    except (OSError, PermissionError):
        return None


def _regex_match_count(pattern: str, content: str) -> int:
    try:
        return len(re.findall(pattern, content))
    except re.error as exc:
        raise ValueError(f"Invalid regex /{pattern}/: {exc}") from exc


def run_single_assertion(
    assertion: dict[str, Any],
    project_root: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(project_root or DEFAULT_PROJECT_ROOT).resolve()
    a_type = assertion.get("type", "")
    pattern = assertion.get("pattern") or assertion.get("query", "")
    description = assertion.get("description", "") or f"{a_type}: {pattern}"

    if a_type not in _VALID_ASSERTION_TYPES:
        return {
            "type": a_type,
            "description": description,
            "passed": True,
            "detail": f"Skipped non-machine assertion type: {a_type!r}",
            "skipped": True,
        }
    if not pattern:
        return {
            "type": a_type,
            "description": description,
            "passed": False,
            "detail": f"Missing 'pattern' for assertion type '{a_type}'",
        }

    result: dict[str, Any] = {
        "type": a_type,
        "description": description,
        "passed": False,
        "detail": "",
    }

    if a_type == "grep":
        file_field = (
            assertion.get("file")
            or assertion.get("file_pattern")
            or assertion.get("target")
            or assertion.get("path")
            or assertion.get("expected")
            or ""
        )
        if not file_field:
            result["detail"] = "Missing 'file' field for grep assertion"
            return result

        if "*" in file_field or "?" in file_field:
            file_paths = list(root.glob(file_field))
            if not file_paths:
                result["detail"] = f"No files matching glob '{file_field}'"
                return result
        else:
            file_paths = [root / file_field]

        min_count = assertion.get("min_count", 1)
        total_matches = 0
        try:
            for file_path in file_paths:
                content = _read_file_safe(file_path)
                if content is None:
                    continue
                total_matches += _regex_match_count(pattern, content)
        except ValueError as exc:
            result["detail"] = str(exc)
            return result

        result["passed"] = total_matches >= min_count
        result["detail"] = (
            f"Found {total_matches} match(es) for /{pattern}/ "
            f"(need >= {min_count}) in {file_field}"
        )
        return result

    if a_type == "glob":
        matches = list(root.glob(pattern))
        contains = assertion.get("contains")
        if contains and matches:
            matches = [match for match in matches if contains in (_read_file_safe(match) or "")]
        result["passed"] = len(matches) > 0
        result["detail"] = (
            f"Glob '{pattern}' matched {len(matches)} file(s)"
            + (f" containing '{contains}'" if contains else "")
        )
        return result

    file_field = (
        assertion.get("file")
        or assertion.get("file_pattern")
        or assertion.get("target")
        or assertion.get("path")
        or ""
    )
    if not file_field:
        result["detail"] = "Missing 'file' field for grep_absent assertion"
        return result

    file_path = root / file_field
    content = _read_file_safe(file_path)
    if content is None:
        result["passed"] = True
        result["detail"] = f"File '{file_field}' not found (pattern absent by default)"
        return result

    try:
        count = _regex_match_count(pattern, content)
    except ValueError as exc:
        result["detail"] = str(exc)
        return result
    result["passed"] = count == 0
    result["detail"] = f"Found {count} match(es) for /{pattern}/ in {file_field}"
    return result


def run_spec_assertions(
    db: KnowledgeDB,
    spec: dict[str, Any],
    triggered_by: str,
    project_root: str | Path | None = None,
) -> dict[str, Any]:
    spec_id = spec["id"]
    spec_version = spec["version"]
    assertions = spec.get("_assertions_parsed") or []

    if not assertions:
        return {
            "spec_id": spec_id,
            "title": spec["title"],
            "overall_passed": True,
            "results": [],
            "assertion_count": 0,
            "skipped": True,
        }

    results = []
    for assertion in assertions:
        try:
            results.append(run_single_assertion(assertion, project_root=project_root))
        except Exception as exc:  # pragma: no cover - defensive
            results.append(
                {
                    "type": assertion.get("type", ""),
                    "description": assertion.get("description", "") or "Assertion execution error",
                    "passed": False,
                    "detail": f"Assertion execution error: {exc}",
                }
            )

    machine_results = [result for result in results if not result.get("skipped")]
    overall_passed = all(result["passed"] for result in machine_results) if machine_results else True
    db.insert_assertion_run(
        spec_id=spec_id,
        spec_version=spec_version,
        overall_passed=overall_passed,
        results=results,
        triggered_by=triggered_by,
    )

    return {
        "spec_id": spec_id,
        "title": spec["title"],
        "overall_passed": overall_passed,
        "results": results,
        "assertion_count": len(machine_results),
        "skipped": len(machine_results) == 0 and len(results) > 0,
    }


def run_all_assertions(
    db: KnowledgeDB,
    *,
    triggered_by: str = "manual",
    spec_id: str | None = None,
    project_root: str | Path | None = None,
) -> dict[str, Any]:
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
        result = run_spec_assertions(db, spec, triggered_by, project_root=project_root)
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
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "triggered_by": triggered_by,
        "details": details,
    }


def verify_project(
    *,
    project_root: str | Path | None = None,
    db_path: str | Path | None = None,
    triggered_by: str = "manual",
    spec_id: str | None = None,
) -> dict[str, Any]:
    root = Path(project_root or DEFAULT_PROJECT_ROOT).resolve()
    db = KnowledgeDB(db_path or DEFAULT_DB_PATH)
    try:
        return run_all_assertions(
            db,
            triggered_by=triggered_by,
            spec_id=spec_id,
            project_root=root,
        )
    finally:
        db.close()


def print_summary(summary: dict[str, Any]) -> None:
    if "error" in summary:
        print(f"ERROR: {summary['error']}")
        return

    print("")
    print("=" * 60)
    print(f"  Assertion Results - triggered by: {summary['triggered_by']}")
    print("=" * 60)
    print(f"  Total specs:       {summary['total_specs']}")
    print(f"  With assertions:   {summary['specs_with_assertions']}")
    print(f"  PASSED:            {summary['passed']}")
    print(f"  FAILED:            {summary['failed']}")
    print(f"  Skipped (no def):  {summary['skipped']}")
    print("=" * 60)
    print("")

    failures = [
        detail
        for detail in summary["details"]
        if not detail.get("skipped") and not detail["overall_passed"]
    ]
    if failures:
        print("FAILURES:")
        print("")
        for failure in failures:
            print(f"  [{failure['spec_id']}] {failure['title']}")
            for result in failure["results"]:
                status = "PASS" if result["passed"] else "FAIL"
                print(f"    [{status}] {result['description']}: {result['detail']}")
            print("")

    passes = [
        detail
        for detail in summary["details"]
        if not detail.get("skipped") and detail["overall_passed"]
    ]
    if passes:
        print("PASSED:")
        print("")
        for passed in passes:
            print(f"  [{passed['spec_id']}] {passed['title']} ({passed['assertion_count']} assertions)")
        print("")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run KB assertions against the project codebase")
    parser.add_argument("--project-root", default=None, help="Project root path")
    parser.add_argument("--db", default=None, help="Explicit KB database path")
    parser.add_argument("--pre-build", action="store_true", help="Pre-build gate mode")
    parser.add_argument("--session-start", action="store_true", help="Session-start gate mode")
    parser.add_argument("--spec", default=None, help="Run a single spec ID")
    args = parser.parse_args(argv)

    triggered_by = "manual"
    if args.pre_build:
        triggered_by = "pre-build"
    elif args.session_start:
        triggered_by = "session-start"

    summary = verify_project(
        project_root=args.project_root,
        db_path=args.db,
        triggered_by=triggered_by,
        spec_id=args.spec,
    )
    print_summary(summary)
    if "error" in summary:
        return 1
    return 1 if summary.get("failed", 0) > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
