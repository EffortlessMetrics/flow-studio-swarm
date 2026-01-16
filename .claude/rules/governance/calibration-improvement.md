# Calibration Improvement

The system learns from runs, not from opinions.

## The Rule

> Patterns require 3+ occurrences. Test before deploy.
> Changes require evidence.

## Do

- Wait for 3+ occurrences before treating as pattern
- Test proposed changes against historical runs
- Monitor for 1 week after deployment

## Don't

- Change prompts without evidence ("I think it should...")
- Over-fit to single recent failures
- Ignore recurring detours ("it works, just fires a lot")

## Change Types

- **Prompt update**: Agent behavior needs adjustment
- **Flow modification**: Step sequence needs change
- **Detour addition**: New known fix pattern

> Docs: docs/explanation/WISDOM_PIPELINE.md
