# Membase Operating Model

Membase is designed to bootstrap a three-party development system:

- Prime Builder: proposes and implements approved changes
- Loyal Opposition: challenges proposals and completed work with evidence
- Human AI Engineer: adjudicates disagreement, accepts residual risk, and sets priority

## Evidence Surfaces

Membase treats project truth as a combination of:

1. specifications
2. tests
3. system artifacts
4. observed reality

Observed reality is runtime-derived evidence such as logs, traces, screenshots, deployment state, and direct user-observed behavior. It is not a change-controlled artifact in the same sense as specs, tests, or source code, but it is required to resolve disagreements when source artifacts diverge from runtime behavior.

## Five-Stage Protocol

### Stage 0: Pre-Proposal Artifact Sweep

Check the current governing specs, tests, prior reviews, and runbooks before writing a proposal.

### Stage 1: Proposal

Prime Builder proposes the intended change, scope, risks, and planned verification.

### Stage 2: Proposal Challenge

Loyal Opposition challenges omissions, drift, and insufficient evidence.

### Stage 3: Implementation

Prime Builder implements the approved scope and records the actual file changes and verification results.

### Stage 4: Implementation Challenge / Go-No-Go

Loyal Opposition reviews the completed work and recommends go/no-go with explicit residual risk.

## Why This Matters

The point of the operating model is not only to use two AI tools. The point is to separate implementation and critique so session-local drift, speculative retrieval, and weak recall do not propagate unchecked.
