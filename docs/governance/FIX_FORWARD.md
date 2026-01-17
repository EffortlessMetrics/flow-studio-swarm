# Fix-Forward Philosophy

Fix-forward by default. BLOCKED is rare and literal. Flows complete; gates review.

## Why Fix-Forward?

Mid-flow escalation creates babysitting overhead—humans monitoring runs, answering questions, unblocking agents. Completed flows with documented concerns are reviewable artifacts. Stalled flows are waste.

**The trade:** An imperfect complete run is worth more than a perfect incomplete one. Compute is cheaper than waiting.

## Status Vocabulary

| Status | Meaning | When to Use |
|--------|---------|-------------|
| **VERIFIED** | Work complete, requirements met | Advance without concerns |
| **UNVERIFIED** | Work complete, concerns documented | Critic decides; gate reviews |
| **BLOCKED** | Cannot proceed | Reserved for true blockers |

## BLOCKED is Reserved For

Use BLOCKED only when:

1. **Missing inputs** — Required artifacts literally don't exist
2. **Environment failure** — Infrastructure/tooling broken
3. **Non-derivable decision** — Human decision required that cannot be reasonably assumed
4. **Boundary violation** — Secrets in diff, security breach

**NOT for:**
- Ambiguity → document assumption → UNVERIFIED
- Uncertainty → document concern → UNVERIFIED
- Style issues → route to auto-linter
- "Needs review" → that's what gates are for

## Assumptive-but-Transparent Work

When facing ambiguity:

1. Make a reasonable assumption
2. Document explicitly: what, why, impact if wrong
3. Note what would change if assumption is wrong
4. Proceed with UNVERIFIED status

This enables re-running flows with better inputs. Each flow is designed to be **run again** with refined inputs.

## The Pattern

```
Ambiguity detected
  → Can I read my inputs?
    → Yes → Make documented assumption → UNVERIFIED
    → No (inputs don't exist) → BLOCKED
```

## Examples

| Situation | Status | Reason |
|-----------|--------|--------|
| Spec ambiguous about edge case | UNVERIFIED | Assumption documented |
| Test framework unknown | UNVERIFIED | Picked pytest, documented |
| Input artifact missing | BLOCKED | Cannot proceed without it |
| Style doesn't match repo | UNVERIFIED | Route to linter |
| API credentials missing | BLOCKED | Environment failure |

## See Also

- [docs/CONTEXT_BUDGETS.md](../CONTEXT_BUDGETS.md) — How budgets control input selection
- [docs/ROUTING_PROTOCOL.md](../ROUTING_PROTOCOL.md) — How routing decisions work
- [docs/AGOPS_MANIFESTO.md](../AGOPS_MANIFESTO.md) — Factory model philosophy
