# Calibration Signals: Metrics and Collection

Track these signals to know if the system is improving.

## Primary Metrics

| Signal | What It Measures | Target |
|--------|------------------|--------|
| **Detour rate by flow** | How often flows go off-road | < 20% |
| **Human intervention rate** | How often humans must intervene | < 5% |
| **Average run cost** | Compute spend per completed run | Trend down |
| **Time to merged PR** | Signal → approved merge | Trend down |

## Secondary Metrics

| Signal | What It Reveals |
|--------|-----------------|
| Runs requiring human intervention | What the system can't handle |
| Detour frequency by type | What keeps breaking |
| Time to approval | Where humans spend review time |
| Gate false positives | Unnecessary bounces |
| Gate false negatives | Escaped issues |

## Signal Collection

Signals are collected in:
```
swarm/calibration/
├── signals.jsonl           # Append-only signal log
├── patterns.json           # Detected patterns (3+ occurrences)
├── proposals/              # Change proposals
│   ├── prompt-001.json
│   └── flow-002.json
└── experiments/            # A/B test results
    └── exp-001.json
```

## Signal Schema

Each signal entry in `signals.jsonl`:

```json
{
  "timestamp": "ISO8601",
  "run_id": "string",
  "signal_type": "detour | intervention | escape | duration",
  "details": {
    "flow_key": "build",
    "step_id": "step-3",
    "value": "varies by type"
  }
}
```

## Dashboard Metrics

| Metric | Calculation | Review Frequency |
|--------|-------------|------------------|
| Detour rate by flow | detours / total_steps | Weekly |
| Human intervention rate | interventions / total_runs | Weekly |
| Average run cost | total_cost / completed_runs | Weekly |
| Time to merged PR | merged_at - signal_at | Per run |
| Pattern detection rate | patterns_found / week | Weekly |
| Change success rate | successful_changes / proposed | Monthly |

## Trend Analysis

Track week-over-week:
- Is detour rate decreasing?
- Is human intervention rate decreasing?
- Is run cost stable or decreasing?
- Is time to merge stable or decreasing?

Regression on any metric triggers investigation.

## The Rule

> Primary metrics define success. Secondary metrics reveal causes.
> Trend down on cost and time. Trend down on intervention rate.
> Regression triggers investigation, not panic.

---

## See Also
- [calibration-loop.md](./calibration-loop.md) - The learning loop and feedback mechanisms
- [calibration-improvement.md](./calibration-improvement.md) - Pattern detection and improvement process
- [evidence-discipline.md](./evidence-discipline.md) - What counts as evidence
- [off-road-logging.md](../artifacts/off-road-logging.md) - Routing decision audit trail
