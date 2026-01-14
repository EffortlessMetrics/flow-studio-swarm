# Token Compression

## Purpose

Compression patterns reduce token usage while preserving information value. Heavy context loaders are multipliers, not waste.

## The Rule

> Summarize, point, structure. Never transcribe.
> One agent compresses; many agents benefit.

## Heavy Loaders Compress for Downstream

The economics:
- One agent reads 50k tokens, produces 2k summary
- Ten downstream agents each receive 2k instead of 50k
- Math: 50k + (10 × 2k) = 70k vs. 10 × 50k = 500k

Heavy loading is a multiplier, not waste.

Heavy context loaders:
- `context-loader`: 20-50k input → 2-5k structured output
- `impact-analyzer`: Full codebase scan → impact summary

## Summarize Before Loading

Large artifacts should be compressed before loading:

| Artifact Size | Action |
|---------------|--------|
| < 2k tokens | Load directly |
| 2k-10k tokens | Consider summary |
| > 10k tokens | Always summarize first |

## Use Paths, Not Contents

When reference exists elsewhere:

```markdown
# Good: Path reference
See implementation in `src/auth.py:42-85`

# Bad: Inline content
Here's the implementation:
[50 lines of code...]
```

## Structured Over Prose

```json
// Good: Structured output
{
  "status": "UNVERIFIED",
  "concerns": [
    { "severity": "HIGH", "file": "src/auth.py", "line": 42 }
  ]
}

// Bad: Prose output
"I found an issue in the authentication module. Specifically,
on line 42 of the src/auth.py file, there's a high severity
concern that needs to be addressed..."
```

## Evidence Pointers Over Inline Evidence

```markdown
# Good: Pointer
Test results: `RUN_BASE/build/test_output.log` (47 passed, 0 failed)

# Bad: Inline
Test results:
[45 lines of pytest output]
```

## Diff Over Full File

```diff
# Good: Diff
@@ -42,3 +42,5 @@
 def authenticate(user, password):
+    if not user or not password:
+        raise ValueError("Credentials required")
     return check_credentials(user, password)

# Bad: Full file with changes noted
"Here's the updated auth.py file: [entire 200-line file]"
```

## Scent Trail vs Handoff

| Artifact | Include | Exclude |
|----------|---------|---------|
| **Scent Trail** | Key decisions, rationale, rejected alternatives | Full reasoning chains, exploration, abandoned approaches |
| **Handoff** | Summary, findings, evidence pointers, routing | Full reasoning, verbose explanations, repeated context |

```json
{
  "decisions": [
    {
      "step": "plan-step-3",
      "decision": "Use OAuth over API keys",
      "rationale": "User requested 'standard login'",
      "confidence": "HIGH"
    }
  ]
}
```

## Receipts Are Compact By Design

Receipts capture:
- What happened (status, duration)
- Evidence pointers (paths to logs)
- Key metrics (counts, not raw output)

```json
{
  "tests": { "passed": 47, "failed": 0, "evidence": "test_output.log" },
  "lint": { "errors": 0, "evidence": "lint_output.log" }
}
```

NOT the full test output or lint report.

---

## See Also
- [token-budgets.md](./token-budgets.md) - Budget allocation
- [token-waste-patterns.md](./token-waste-patterns.md) - Anti-patterns
- [scent-trail.md](../artifacts/scent-trail.md) - Decision provenance
- [handoff-protocol.md](../artifacts/handoff-protocol.md) - Envelope structure
