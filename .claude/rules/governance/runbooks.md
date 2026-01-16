# Runbooks

Runbooks are executable checklists. Valid only if someone unfamiliar can execute them.

## Required Sections

Purpose | Prerequisites | Steps | Verification | Rollback | Troubleshooting

## Writing Principles

- Steps: imperative and bounded
- Verification: commands and evidence paths (not "seems fine")
- Decision points: explicit criteria
- Every step has expected output

## Validation

- Test it yourself before publishing
- Have someone unfamiliar execute it
- Every question becomes documentation
- Verify idempotence (run twice, no harm)

## The Rule

- If a human cannot follow it linearly, it's not a runbook
- "Use your judgment" is banned; be explicit
- No rollback plan = not ready to publish

> Docs: docs/runbooks/RUNBOOK_STRUCTURE.md
