# Agent-Generated Commits

Special requirements for commits created by agents in the swarm.

## Receipt References Required

Agent commits MUST include evidence pointers:

```
feat: implement OAuth2 callback handler

Implements the callback handler for OAuth2 authorization flow
as specified in ADR-005.

Receipt: swarm/runs/abc123/build/receipts/step-3-code-implementer.json
Tests: 12 passed, 0 failed
Coverage: 89% on new code

Fixes #234
```

## Pre-Commit Hooks Must Pass

Agents MUST NOT bypass hooks:

```bash
# NEVER use:
git commit --no-verify  # Skips hooks
git commit -n           # Same thing

# ALWAYS let hooks run:
git commit -m "feat: add feature"  # Hooks validate
```

## Subject Line Conventions

Agent commits use standard types, NOT automation markers:

```bash
# GOOD: Standard commit type
git commit -m "feat: add rate limiting to API"

# BAD: Automation markers in subject
git commit -m "[AUTO] feat: add rate limiting"
git commit -m "AI: add rate limiting to API"
```

Automation is evident from the receipt reference in the body, not the subject.

## Evidence Binding

Agent commits bind to evidence via the body:

| Element | Purpose | Example |
|---------|---------|---------|
| Receipt path | Proof of execution | `Receipt: swarm/runs/.../step-3-code.json` |
| Test results | Verification summary | `Tests: 12 passed, 0 failed` |
| Coverage | Quality indicator | `Coverage: 89% on new code` |
| Issue ref | Traceability | `Fixes #234` |

## The Rule

> Agent commits reference receipts. No hook bypasses.
> Standard types only—no [AUTO] or AI: markers.
> Evidence is in the body, not the subject.

---

## See Also
- [commit-message-format.md](./commit-message-format.md) - Message format and types
- [commit-atomicity.md](./commit-atomicity.md) - Atomic and bisectable commits
- [receipt-schema.md](../artifacts/receipt-schema.md) - Receipt requirements
- [boundary-automation.md](./boundary-automation.md) - Publish gate checks
