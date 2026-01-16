# Calibration

The system learns from runs, not opinions.

## The Rule

- Patterns require **3+ occurrences** before action
- Test proposed changes against historical runs
- Monitor for 1 week after deployment
- Don't change prompts without evidence
- Don't over-fit to single recent failures

## Primary Signals

| Signal | Target |
|--------|--------|
| Detour rate by flow | < 20% |
| Human intervention rate | < 5% |
| Average run cost | Trend down |
| Time to merged PR | Trend down |

Regression triggers investigation, not panic.

> Docs: docs/explanation/WISDOM_PIPELINE.md
