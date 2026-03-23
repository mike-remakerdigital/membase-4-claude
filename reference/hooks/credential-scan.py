#!/usr/bin/env python3
"""
Claude Code PreToolUse hook — Hardcoded Credential & Secret Scanner.

Intercepts Write and Edit tool calls and blocks content that contains
hardcoded credentials, API keys, cloud FQDNs, or other environment-specific
values that should be sourced from environment variables.

Stdin:  JSON {"tool_name": "Write"|"Edit", "tool_input": {...}, ...}
Stdout: JSON {"decision": "block", "reason": "..."} or {}
Exit:   Always 0

This hook is FAIL-OPEN for parse errors (only blocks on positive match).

Configuration:
  Customize the pattern groups below for your cloud provider and project.
  The reference patterns cover AWS, Azure, and GCP common credential formats.

Part of the Membase for Claude reference implementation.
See: https://github.com/mike-remakerdigital/membase-4-claude
"""

import json
import re
import sys


# ---------------------------------------------------------------------------
# Credential patterns — customize for your project
# ---------------------------------------------------------------------------

# Cloud provider FQDNs (uncomment the sections relevant to your stack)

# Azure
_FQDN_PATTERNS = [
    re.compile(r'["\']https?://[a-z0-9-]+\.[a-z0-9-]+\.[a-z0-9]+\.azurecontainerapps\.io[^"\']*["\']'),
    re.compile(r'["\']https?://[a-z0-9-]+\.redis\.cache\.windows\.net[^"\']*["\']'),
    re.compile(r'["\']https?://[a-z0-9-]+\.documents\.azure\.com[^"\']*["\']'),
    re.compile(r'["\']https?://[a-z0-9-]+\.vault\.azure\.net[^"\']*["\']'),
]

# AWS (uncomment if using AWS)
# _FQDN_PATTERNS += [
#     re.compile(r'["\']https?://[a-z0-9-]+\.execute-api\.[a-z0-9-]+\.amazonaws\.com[^"\']*["\']'),
#     re.compile(r'["\']https?://[a-z0-9-]+\.s3\.[a-z0-9-]+\.amazonaws\.com[^"\']*["\']'),
#     re.compile(r'["\']https?://[a-z0-9-]+\.rds\.[a-z0-9-]+\.amazonaws\.com[^"\']*["\']'),
# ]

# GCP (uncomment if using GCP)
# _FQDN_PATTERNS += [
#     re.compile(r'["\']https?://[a-z0-9-]+-[a-z0-9]+\.a\.run\.app[^"\']*["\']'),
#     re.compile(r'["\']https?://[a-z0-9-]+\.firebaseio\.com[^"\']*["\']'),
# ]

# API key patterns — customize the prefix for your project
# Example: if your keys start with "sk_" or "pk_", add those patterns
_API_KEY_PATTERNS = [
    # Generic patterns (common across many services)
    re.compile(r'["\'](?:sk|pk)_(live|test)_[A-Za-z0-9]{20,}["\']'),   # Stripe-style keys
    re.compile(r'["\']AKIA[0-9A-Z]{16}["\']'),                          # AWS access key IDs
    re.compile(r'["\']ghp_[A-Za-z0-9]{36}["\']'),                       # GitHub personal tokens
    re.compile(r'["\']xox[bpors]-[A-Za-z0-9-]{10,}["\']'),              # Slack tokens
    # Add your project's key prefix pattern here:
    # re.compile(r'["\']myapp_[A-Za-z0-9]{16,}["\']'),
]

# Resource/subscription IDs (UUIDs in assignment context)
_RESOURCE_ID_PATTERNS = [
    re.compile(
        r'(?:subscription|client.id|tenant.id|managed.identity|project.id)\s*[:=]\s*'
        r'["\'][0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}["\']',
        re.IGNORECASE,
    ),
]

# Connection strings
_CONN_STRING_PATTERNS = [
    re.compile(r'["\']AccountEndpoint=https://[^"\']+;AccountKey=[^"\']+["\']'),
    re.compile(r'["\']DefaultEndpointsProtocol=https;[^"\']+["\']'),
    re.compile(r'["\']Server=tcp:[^"\']+\.database\.windows\.net[^"\']*["\']'),
    re.compile(r'["\']postgresql://[^"\']+:[^"\']+@[^"\']+["\']'),
    re.compile(r'["\']mongodb\+srv://[^"\']+:[^"\']+@[^"\']+["\']'),
    re.compile(r'["\']redis://:[^"\']+@[^"\']+["\']'),
]


# ---------------------------------------------------------------------------
# Exclusions — files where these patterns are expected
# Customize for your project's directory structure.
# ---------------------------------------------------------------------------

_EXCLUDED_PATHS = [
    # Memory/documentation files (not deployed code)
    re.compile(r'memory[/\\]'),
    re.compile(r'MEMORY\.md$'),
    re.compile(r'CLAUDE\.md$'),
    # Hook files themselves (this file contains the patterns!)
    re.compile(r'\.claude[/\\]hooks[/\\]'),
    # Documentation
    re.compile(r'wiki[/\\]'),
    re.compile(r'docs[/\\]'),
    re.compile(r'\.html$'),
    # Environment config files (where env vars are DEFINED)
    re.compile(r'\.env'),
    re.compile(r'\.local$'),
    # Deploy scripts that reference resource names
    re.compile(r'deploy[/\\].*\.(ps1|sh)$'),
    # Docker/container config
    re.compile(r'Dockerfile'),
    re.compile(r'docker-compose'),
    # Lock files and minified assets
    re.compile(r'package-lock\.json'),
    re.compile(r'\.min\.js$'),
]


def _is_excluded(file_path: str) -> bool:
    """Check if the file path is excluded from scanning."""
    return any(p.search(file_path) for p in _EXCLUDED_PATHS)


def _scan_content(content: str) -> list[str]:
    """Scan content for hardcoded credentials/FQDNs. Returns list of findings."""
    findings = []

    for pattern in _FQDN_PATTERNS:
        matches = pattern.findall(content)
        if matches:
            for match in matches:
                findings.append(f"Hardcoded cloud FQDN: {match[:80]}...")

    for pattern in _API_KEY_PATTERNS:
        matches = pattern.findall(content)
        if matches:
            findings.append("Hardcoded API key detected")

    for pattern in _RESOURCE_ID_PATTERNS:
        matches = pattern.findall(content)
        if matches:
            findings.append("Hardcoded resource/subscription ID")

    for pattern in _CONN_STRING_PATTERNS:
        matches = pattern.findall(content)
        if matches:
            findings.append("Hardcoded connection string")

    return findings


def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
    except (json.JSONDecodeError, Exception):
        # Can't parse — fail OPEN (don't block on parse error)
        print(json.dumps({}))
        sys.exit(0)

    tool_name = data.get("tool_name", "")

    # Only scan Write and Edit tools
    if tool_name not in ("Write", "Edit"):
        print(json.dumps({}))
        sys.exit(0)

    tool_input = data.get("tool_input", {})

    # Get the file path
    file_path = tool_input.get("file_path", "")
    if not file_path or _is_excluded(file_path):
        print(json.dumps({}))
        sys.exit(0)

    # Get content to scan
    if tool_name == "Write":
        content = tool_input.get("content", "")
    elif tool_name == "Edit":
        content = tool_input.get("new_string", "")
    else:
        content = ""

    if not content:
        print(json.dumps({}))
        sys.exit(0)

    try:
        findings = _scan_content(content)
    except Exception:
        # Pattern matching failed — fail OPEN
        print(json.dumps({}))
        sys.exit(0)

    if findings:
        reason = (
            f"BLOCKED: Hardcoded environment-specific values detected "
            f"in {file_path}:\n"
            + "\n".join(f"  - {f}" for f in findings[:5])
            + "\n\nAll FQDNs, API keys, connection strings, and resource IDs "
            "MUST come from environment variables. "
            "Use os.environ.get() or equivalent."
        )
        print(json.dumps({"decision": "block", "reason": reason}))
    else:
        print(json.dumps({}))

    sys.exit(0)


if __name__ == "__main__":
    main()
