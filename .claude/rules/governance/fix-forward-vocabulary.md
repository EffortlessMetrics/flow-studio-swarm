# Fix-Forward Vocabulary

Fix-forward by default. BLOCKED is rare and literal.

## Status Meanings

- **VERIFIED**: Work complete, requirements met → advance
- **UNVERIFIED**: Work complete, concerns documented → critic decides
- **BLOCKED**: Cannot proceed → only for missing inputs, env failure, boundary violation

## The Rule

> Ambiguity → documented assumption → UNVERIFIED
> Uncertainty → documented concern → UNVERIFIED
> Style issues → route to auto-linter
> Flows complete; gates review.

## BLOCKED is Reserved For

1. Missing input artifacts (literally don't exist)
2. Environment/infrastructure failure
3. Non-derivable human decision needed
4. Boundary violation (secrets in diff)

NOT for: ambiguity, uncertainty, style, "needs review"

> Docs: docs/governance/FIX_FORWARD.md
