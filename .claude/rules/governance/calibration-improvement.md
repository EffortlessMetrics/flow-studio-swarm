# Calibration Improvement: Pattern Detection and Change Process

How to detect patterns, propose changes, test them, and deploy safely.

## The 3+ Rule

A pattern exists when:
- Same failure type occurs 3+ times
- Same detour fires 3+ times
- Same human intervention type 3+ times

Below 3 occurrences: noise.
At 3+ occurrences: pattern requiring action.

## Pattern Schema

```json
{
  "pattern_id": "string",
  "type": "failure | detour | intervention | escape",
  "occurrences": [
    {
      "run_id": "string",
      "timestamp": "ISO8601",
      "details": {}
    }
  ],
  "first_seen": "ISO8601",
  "last_seen": "ISO8601",
  "count": "number",
  "status": "new | proposed | testing | deployed | rejected"
}
```

## Improvement Process

### 1. Collect Signals

Flow 7 extracts signals from every completed run:
- What detours fired?
- What human interventions occurred?
- What escaped to gate or beyond?
- What took longer than expected?

### 2. Identify Patterns

Weekly (or continuous) pattern detection:
- Group by failure type
- Count occurrences
- Promote to pattern at 3+

### 3. Propose Change

For each pattern, propose ONE of:

| Change Type | When to Use | Example |
|-------------|-------------|---------|
| **Prompt update** | Agent behavior needs adjustment | Add requirement to teaching notes |
| **Flow modification** | Step sequence needs change | Add pre-emptive step |
| **Agent addition** | New capability needed | Add specialized fixer agent |
| **Detour addition** | New known fix pattern | Add to detour catalog |

### 4. Test Against Historical Runs

Before deploying:
- Replay affected runs with proposed change
- Compare outcomes (success rate, detour rate, cost)
- Require improvement on target metric

```json
{
  "experiment_id": "exp-001",
  "change": "prompt-001",
  "baseline_runs": ["run-001", "run-005", "run-008"],
  "baseline_outcomes": {
    "success_rate": 0.33,
    "detour_rate": 0.67
  },
  "experiment_outcomes": {
    "success_rate": 0.67,
    "detour_rate": 0.33
  },
  "improvement": {
    "success_rate": "+34%",
    "detour_rate": "-34%"
  },
  "recommendation": "deploy"
}
```

### 5. Deploy with Monitoring

After deployment:
- Monitor target metric for 1 week
- Compare to pre-change baseline
- Rollback if regression detected

## Calibration Cadence

| Activity | Frequency | Owner |
|----------|-----------|-------|
| Signal collection | Per run | Flow 7 |
| Pattern detection | Weekly | Wisdom analysis |
| Change proposal | When pattern detected | Flow 7 |
| Historical testing | Before deploy | Automated |
| Deployment | After test passes | Human approval |
| Monitoring | 1 week post-deploy | Automated |
| Trend review | Weekly | Human |

## Anti-Patterns

### Changing Prompts Without Evidence

**Wrong:**
```
"I think the code-implementer should be more careful about error handling"
→ Update prompt
```

**Right:**
```
"Pattern detected: 5 runs failed due to missing error handling"
→ Propose change
→ Test against historical runs
→ Deploy if improvement confirmed
```

### Over-Fitting to Recent Failures

**Wrong:**
```
"Last run had a weird edge case, add handling for it"
```

**Right:**
```
"Wait for 3+ occurrences before treating as pattern"
→ Single occurrence = noise
→ 3+ occurrences = signal
```

### Ignoring Recurring Failures

**Wrong:**
```
"That detour fires a lot, but it works"
```

**Right:**
```
"That detour fires 15/20 runs"
→ Pattern detected
→ Propose pre-emptive fix
→ Reduce detour rate
```

## The Economics

Calibration is an investment:
- **Cost:** Analysis compute, historical replay, monitoring
- **Return:** Reduced detour rate, reduced intervention, lower run cost

Break-even typically occurs when:
- A single prevented human intervention saves 30+ minutes
- A single prevented detour saves ~$0.50 in compute
- Pattern-based improvements compound over runs

## The Rule

> Changes require evidence. Patterns require 3+ occurrences.
> Test before deploy. Monitor after deploy.
> The system learns from runs, not from opinions.

## Current Implementation Status

| Component | Status | Location |
|-----------|--------|----------|
| Signal collection | Designed | This spec |
| Pattern detection | Designed | This spec |
| Change proposals | Designed | This spec |
| Historical replay | Aspirational | Not implemented |
| Monitoring | Aspirational | Not implemented |

---

## See Also
- [calibration-loop.md](./calibration-loop.md) - The learning loop and feedback mechanisms
- [calibration-signals.md](./calibration-signals.md) - Metrics and signal collection
- [flow-charters.md](./flow-charters.md) - Flow 7 (Wisdom) charter
- [evidence-discipline.md](./evidence-discipline.md) - What counts as evidence
