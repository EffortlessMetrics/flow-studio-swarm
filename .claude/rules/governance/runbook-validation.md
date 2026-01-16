# Runbook Validation

A runbook is valid only if someone unfamiliar can execute it successfully.

## Validation Checklist
- [ ] All six required sections present
- [ ] Every step has expected output
- [ ] Decision points explicitly documented
- [ ] Rollback plan exists for destructive actions
- [ ] Time estimates included

## Test Before Publishing
1. Execute it yourself
2. Have someone unfamiliar execute it
3. Update based on friction (every question → documentation)
4. Verify idempotence (run twice, no harm)

## Anti-Patterns
- "Use your judgment" → Be explicit about criteria
- Missing expected outputs → Show what success looks like
- Assumed context → State all prerequisites
- No rollback plan → Plan retreat before advance

## The Rule
- Test it before publishing
- Every question becomes documentation
- If running twice breaks things, add guards

> Skill: runbook-validation
> Docs: docs/runbooks/RUNBOOK_STRUCTURE.md
