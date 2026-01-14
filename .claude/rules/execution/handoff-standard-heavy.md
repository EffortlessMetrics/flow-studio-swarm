# Standard and Heavy Handoffs

## Purpose

Standard handoffs transfer context between consecutive steps (500-2000 tokens). Heavy handoffs cross flow boundaries with comprehensive context (2000-5000 tokens).

## The Rule

> Standard handoffs include summary, decisions, evidence pointers, and assumptions.
> Heavy handoffs add domain-specific sections (interfaces, dependencies, test strategy).
> Always use pointers, not inline content.

## Standard Handoff: Step N to Step N+1

Used between consecutive steps within the same flow.

```json
{
  "meta": {
    "step_id": "build-step-3",
    "agent_key": "code-implementer"
  },
  "status": "UNVERIFIED",
  "summary": {
    "what_i_did": "Implemented REQ-001 through REQ-005",
    "what_i_found": "REQ-003 has ambiguous edge case",
    "key_decisions": [
      "Used existing auth library (per ADR-005)",
      "Assumed 24h session duration (not specified)"
    ],
    "evidence": {
      "artifacts_produced": ["src/auth.py", "tests/test_auth.py"],
      "commands_run": ["pytest tests/test_auth.py -v"],
      "measurements": { "tests_passed": 12, "tests_failed": 0, "coverage": "78%" }
    }
  },
  "assumptions": [
    {
      "assumption": "Session duration is 24 hours",
      "why": "Not specified in requirements",
      "impact_if_wrong": "Would need config change"
    }
  ],
  "routing": {
    "recommendation": "CONTINUE",
    "reason": "Ready for critic review"
  }
}
```

### Standard Handoff Elements

| Section | Purpose |
|---------|---------|
| `meta` | Identifies source step and agent |
| `summary.what_i_did` | Actions taken (terse) |
| `summary.key_decisions` | Choices that affect downstream |
| `summary.evidence` | Pointers, not content |
| `assumptions` | Explicit with rationale and impact |
| `routing` | Clear next-step recommendation |

## Heavy Handoff: Flow Boundary

Used when crossing from one flow to another (e.g., Plan to Build).

```json
{
  "meta": {
    "step_id": "plan-final",
    "flow_key": "plan",
    "agent_key": "plan-synthesizer"
  },
  "status": "VERIFIED",
  "summary": {
    "what_i_did": "Completed architectural planning phase",
    "what_i_found": "Feature is well-scoped, moderate complexity",
    "key_decisions": [
      "OAuth with PKCE flow (ADR-005)",
      "PostgreSQL session storage (ADR-006)",
      "Rate limiting via Redis (ADR-007)"
    ],
    "evidence": {
      "artifacts_produced": [
        "RUN_BASE/plan/adr-005.md",
        "RUN_BASE/plan/contracts.md",
        "RUN_BASE/plan/work_plan.md",
        "RUN_BASE/plan/test_plan.md"
      ]
    }
  },
  "plan_summary": {
    "work_items": 8,
    "estimated_complexity": "MEDIUM",
    "key_interfaces": [
      "AuthService.authenticate(credentials) -> Token",
      "AuthService.refresh(token) -> Token",
      "AuthService.revoke(token) -> void"
    ],
    "dependencies": ["auth-library: ^2.0.0", "redis: ^4.0.0"],
    "test_strategy": "Unit tests for auth logic, integration tests for token flow"
  },
  "routing": {
    "recommendation": "CONTINUE",
    "next_step_suggestion": "build-step-0",
    "reason": "Plan complete, ready for implementation"
  }
}
```

### Heavy Handoff Elements

| Section | Purpose |
|---------|---------|
| `plan_summary.work_items` | Scope sizing for Build |
| `plan_summary.key_interfaces` | API contracts for implementation |
| `plan_summary.dependencies` | What to install before coding |
| `plan_summary.test_strategy` | Testing approach for test authors |

## Common Mistakes

### Transcribing Instead of Summarizing

```json
// BAD
{ "test_output": "===== test session starts =====\n..." }

// GOOD
{ "tests": { "passed": 47, "failed": 0, "evidence": "RUN_BASE/build/test_output.log" } }
```

### Re-explaining Prior Decisions

```json
// BAD - redundant with scent trail
{ "summary": { "background": "As you may recall, in step 2 we decided to use OAuth..." } }

// GOOD - reference scent trail
{ "summary": { "what_i_did": "Implemented OAuth callback (per scent trail decision)" } }
```

### Missing Evidence Pointers

```json
// BAD - claims without evidence
{ "summary": { "what_i_did": "Fixed all the bugs and tests pass" } }

// GOOD - evidence pointers
{
  "summary": {
    "what_i_did": "Fixed validation bug in auth module",
    "evidence": {
      "artifacts_modified": ["src/auth.py:42-48"],
      "test_evidence": "RUN_BASE/build/test_output.log",
      "measurements": { "tests_passed": 47, "tests_failed": 0 }
    }
  }
}
```

## Size Reference

| Handoff Type | Target Tokens | Typical JSON Lines |
|--------------|---------------|-------------------|
| Standard | 500-2000 | 30-60 lines |
| Heavy | 2000-5000 | 70-120 lines |

## See Also

- [handoff-minimal.md](./handoff-minimal.md) - Minimal handoff examples for microloops
- [handoff-patterns.md](./handoff-patterns.md) - Sizing guidelines and compression patterns
- [handoff-protocol.md](../artifacts/handoff-protocol.md) - Envelope schema definition
- [context-discipline.md](./context-discipline.md) - What gets loaded on receive
