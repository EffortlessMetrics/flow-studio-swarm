# Calibration Metrics

Track these to know if the system is improving.

## Primary Signals

| Signal | Target | Why |
|--------|--------|-----|
| Detour rate by flow | < 20% | High rate = missing detours or poor prompts |
| Human intervention rate | < 5% | High rate = incomplete automation |
| Average run cost | Trend down | Efficiency improving |
| Time to merged PR | Trend down | End-to-end velocity |

## Secondary Signals

| Signal | Target | Why |
|--------|--------|-----|
| Microloop iterations | < 3 avg | High = poor first attempts |
| Receipt completeness | > 95% | Low = missing evidence |
| Navigator invocation rate | < 30% | High = deterministic paths missing |

## What Triggers Investigation

- Regression on any primary metric
- 3+ occurrences of same failure pattern
- Significant cost increase without scope increase

## Rules

- Patterns require 3+ occurrences before action
- Test changes against historical runs before deploy
- Monitor for 1 week after deployment
- Regression triggers investigation, not panic

See also: [WISDOM_PIPELINE.md](./WISDOM_PIPELINE.md)
