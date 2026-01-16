---
name: pr-review
description: Review pull requests against intent and evidence. Use when reviewing PRs or validating changes before merge.
---
# PR Review

1. Verify against intent source (spec, ADR, work plan).
2. Check evidence for all claims (exit codes + logs + artifacts).
3. Enforce bounded scope (no opportunistic refactors).
4. Mark hotspots and risks with file:line references.
5. Prefer fix-forward: document concerns → UNVERIFIED.
6. Output: VERIFIED / UNVERIFIED / BLOCKED with evidence paths.
