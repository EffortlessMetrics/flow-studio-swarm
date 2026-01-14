# Handoff Examples

Detailed examples of minimal, standard, and heavy handoffs. Use these as templates for different handoff scenarios.

For sizing guidelines and compression patterns, see [handoff-patterns.md](./handoff-patterns.md).

---

## Minimal Handoff: Critic to Author

Used in microloops where a critic returns focused feedback to an author for iteration.

### Good Example

```json
{
  "status": "UNVERIFIED",
  "summary": {
    "what_i_found": "1 HIGH issue"
  },
  "concerns": [
    {
      "severity": "HIGH",
      "description": "Missing input validation",
      "location": "src/auth.py:42",
      "recommendation": "Add validation before database query"
    }
  ],
  "routing": {
    "recommendation": "LOOP",
    "can_further_iteration_help": true
  }
}
```

**Why it works:**
- Focused on one issue
- Clear location with file and line number
- Actionable recommendation
- ~200 tokens

### Bad Example

```json
{
  "status": "UNVERIFIED",
  "summary": {
    "what_i_did": "I carefully reviewed the entire codebase looking for issues...",
    "what_i_found": "After extensive analysis of the authentication module, I discovered that there are several concerns that need to be addressed. The first issue relates to input validation which is critically important for security. The second issue involves error handling which could be improved. The third issue..."
  },
  "concerns": [
    {
      "severity": "HIGH",
      "description": "The validate_token function in the auth module does not properly validate user input before passing it to the database query, which could potentially lead to SQL injection vulnerabilities if an attacker were to craft malicious input...",
      "location": "src/auth.py",
      "recommendation": "You should add proper input validation by sanitizing the input, checking for malicious characters, and using parameterized queries..."
    }
  ]
}
```

**Why it fails:**
- Verbose prose wastes tokens
- Missing line number makes fixing harder
- Over-explained concerns dilute focus
- ~800 tokens for the same information

---

## Standard Handoff: Step N to Step N+1

Used between consecutive steps within the same flow.

### Good Example

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
      "artifacts_produced": [
        "src/auth.py",
        "tests/test_auth.py"
      ],
      "commands_run": [
        "pytest tests/test_auth.py -v"
      ],
      "measurements": {
        "tests_passed": 12,
        "tests_failed": 0,
        "coverage": "78%"
      }
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

**Why it works:**
- Complete but concise summary
- Evidence pointers (not inline content)
- Assumptions explicitly documented with impact
- ~800 tokens

### Key Elements

| Section | Purpose |
|---------|---------|
| `meta` | Identifies source step and agent |
| `summary.what_i_did` | Actions taken (terse) |
| `summary.key_decisions` | Choices that affect downstream |
| `summary.evidence` | Pointers, not content |
| `assumptions` | Explicit with rationale and impact |
| `routing` | Clear next-step recommendation |

---

## Heavy Handoff: Flow Boundary

Used when crossing from one flow to another (e.g., Plan to Build).

### Good Example: Flow 2 (Plan) to Flow 3 (Build)

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
      "Use existing auth library (ADR-005)",
      "PostgreSQL session storage (ADR-006)",
      "Rate limiting via Redis (ADR-007)"
    ],
    "evidence": {
      "artifacts_produced": [
        "RUN_BASE/plan/adr-005.md",
        "RUN_BASE/plan/adr-006.md",
        "RUN_BASE/plan/adr-007.md",
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
    "dependencies": [
      "auth-library: ^2.0.0",
      "redis: ^4.0.0"
    ],
    "test_strategy": "Unit tests for auth logic, integration tests for token flow"
  },
  "routing": {
    "recommendation": "CONTINUE",
    "next_step_suggestion": "build-step-0",
    "reason": "Plan complete, ready for implementation"
  }
}
```

**Why it works:**
- Comprehensive context for flow boundary
- Key interfaces defined upfront
- Dependencies listed for implementation
- Still uses pointers for full artifact content
- ~1500 tokens

### Heavy Handoff Elements

Heavy handoffs include additional sections not present in standard handoffs:

| Section | Purpose |
|---------|---------|
| `plan_summary.work_items` | Scope sizing for Build |
| `plan_summary.key_interfaces` | API contracts for implementation |
| `plan_summary.dependencies` | What to install before coding |
| `plan_summary.test_strategy` | Testing approach for test authors |

---

## Common Mistakes

### Mistake: Transcribing Instead of Summarizing

```json
// BAD
{
  "test_output": "============================= test session starts ==============================\nplatform linux -- Python 3.11.0, pytest-7.4.0\ncollected 47 items\n\ntests/test_auth.py::test_login PASSED\ntests/test_auth.py::test_logout PASSED\n..."
}

// GOOD
{
  "tests": {
    "passed": 47,
    "failed": 0,
    "evidence": "RUN_BASE/build/test_output.log"
  }
}
```

### Mistake: Re-explaining Prior Decisions

```json
// BAD - redundant with scent trail
{
  "summary": {
    "background": "As you may recall, in step 2 we decided to use OAuth because the user requested a standard login flow, and we rejected API keys because they have security issues, and we also rejected magic links because..."
  }
}

// GOOD - reference scent trail
{
  "summary": {
    "what_i_did": "Implemented OAuth callback (per scent trail decision)"
  }
}
```

### Mistake: Missing Evidence Pointers

```json
// BAD - claims without evidence
{
  "summary": {
    "what_i_did": "Fixed all the bugs and tests pass"
  }
}

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

### Mistake: Prose Instead of Structure

```json
// BAD - hard to parse
{
  "summary": "Well, I did a bunch of things today. First I looked at the code and found some issues. Then I fixed them. The main thing was the auth module which had a bug on line 42 where it wasn't checking for null values..."
}

// GOOD - structured and scannable
{
  "summary": {
    "what_i_did": "Fixed null check bug",
    "what_i_found": "Missing validation in auth module",
    "key_decisions": ["Added null check before DB query"]
  },
  "concerns": [
    { "severity": "LOW", "description": "Consider adding rate limiting", "location": "src/auth.py:50" }
  ]
}
```

---

## Size Reference

| Handoff Type | Target Tokens | Typical JSON Lines |
|--------------|---------------|-------------------|
| Minimal | <500 | 15-25 lines |
| Standard | 500-2000 | 30-60 lines |
| Heavy | 2000-5000 | 70-120 lines |

---

## See Also
- [handoff-patterns.md](./handoff-patterns.md) - Sizing guidelines and compression patterns
- [handoff-protocol.md](../artifacts/handoff-protocol.md) - Envelope schema definition
- [microloop-rules.md](./microloop-rules.md) - When minimal handoffs are used
- [context-discipline.md](./context-discipline.md) - What gets loaded on receive
