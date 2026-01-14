# Token Budgets

## Purpose

Token budgets allocate context resources by role and step type. Budget allocation is a design tool, not just a cost constraint.

## The Rule

> Work gets 80% of the budget. Coordination gets 20%.
> If coordination exceeds 20%, the flow design is bloated.

## The 80/20 Split

| Category | Budget Share | Purpose |
|----------|--------------|---------|
| Work | 80% | Actual task execution |
| Coordination | 20% | Handoffs, routing, receipts |

## Context Budget by Role

| Role | Context Budget | Rationale |
|------|----------------|-----------|
| Implementer | Higher | Needs codebase context |
| Critic | Lower | Focused on specific output |
| Navigator | Minimal | Compact forensics only |
| Reporter | Low | Summarization from artifacts |

Critics don't need the full implementation context—they review specific output.
Navigators don't need history—they route based on forensic metrics.

## Budget Pressure by Flow Phase

| Flow Phase | Token Pressure | Mitigation |
|------------|----------------|------------|
| Signal | Low | Small inputs |
| Plan | Medium | Summarize research |
| Build | High | Use subagents for exploration |
| Gate | Medium | Compact forensics |
| Wisdom | High | Batch and summarize |

## Per-Step Budgets

| Step Type | Input Budget | Output Budget |
|-----------|--------------|---------------|
| Shaping | 20k tokens | 5k tokens |
| Implementation | 30k tokens | 10k tokens |
| Critic | 25k tokens | 5k tokens |
| Gate | 20k tokens | 3k tokens |

## Budget Overflow Handling

When input exceeds budget:
1. Drop LOW priority items first
2. Truncate MEDIUM priority items
3. Never truncate CRITICAL items (teaching notes, current step spec)
4. Log what was dropped

```json
{
  "budget_overflow": {
    "requested": 45000,
    "allowed": 30000,
    "dropped": [
      { "item": "history_summary", "tokens": 10000, "priority": "LOW" },
      { "item": "old_artifacts", "tokens": 5000, "priority": "MEDIUM" }
    ]
  }
}
```

## Priority Loading Order

When budget is constrained:

```
1. Teaching notes (NEVER drop)
2. Step-specific spec (NEVER drop)
3. Previous step output (truncate if needed)
4. Referenced artifacts (load on-demand)
5. History/scent trail (drop first)
```

## Token Tracking in Receipts

Every receipt includes token counts:

```json
{
  "tokens": {
    "prompt": 12500,
    "completion": 3200,
    "total": 15700
  }
}
```

## Design Signals

When you see:
- Steps consistently over budget → step scope too broad
- High coordination overhead → flow has too many steps
- Repeated content → context discipline failing
- Verbose outputs → structured schemas missing

These are design signals, not just cost issues.

---

## See Also
- [token-compression.md](./token-compression.md) - Compression patterns
- [token-waste-patterns.md](./token-waste-patterns.md) - Anti-patterns
- [context-discipline.md](./context-discipline.md) - Session amnesia rules
- [scarcity-enforcement.md](../governance/scarcity-enforcement.md) - Budgets as design
