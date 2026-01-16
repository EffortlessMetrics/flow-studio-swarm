# Runbook Structure

Runbooks are executable checklists.

## Required Sections

| Section | Purpose |
|---------|---------|
| Purpose | What this accomplishes (1-2 lines) |
| Prerequisites | What must be true before starting |
| Steps | Numbered, one action per step |
| Verification | Commands + expected signals |
| Rollback | How to undo safely |
| Troubleshooting | Common issues and fixes |

## Writing Principles

- Steps MUST be imperative and bounded
- Verification MUST name commands and evidence paths
- "Seems fine" / "should work" is banned

## Validation Checklist

- [ ] All six required sections present
- [ ] Every step has expected output
- [ ] Decision points explicitly documented
- [ ] Rollback plan exists for destructive actions

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
