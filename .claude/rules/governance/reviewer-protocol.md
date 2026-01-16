# Reviewer Protocol

Reviewers route based on intent + evidence + risk. Never on author confidence.

## The Rule
- Verify against **intent source** (spec/ADR/work plan)
- Require **evidence** for claims (exit codes + logs + artifacts)
- Enforce **bounded scope** (no opportunistic refactors)
- Prefer **fix-forward**: document concerns → UNVERIFIED (gate decides)
- BLOCKED is reserved for missing inputs, env failure, or boundary violation

## Reviewer Output
- VERIFIED / UNVERIFIED / BLOCKED
- Evidence present/missing (paths)
- Hotspots / risks (file:line when possible)

> Docs: docs/runbooks/PR_REVIEW.md
