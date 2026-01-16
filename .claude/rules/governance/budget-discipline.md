# Budget Discipline

$30 buys a complete 7-flow run. Track every dollar.

## The Rule

> Run budget: $30. Hard abort at $45.
> Compute is cheap; throwing it away is still waste.

## Abort Triggers

- Run exceeds $45 → ABORT
- Single step exceeds $5 → ABORT (unless Wisdom)
- Same error twice → route to detour, don't burn tokens
- Token burn with no artifact production → ABORT step

## Continue If

- Cumulative cost < $30
- Progress is measurable (receipts show movement)
- Remaining flows are cheap (Gate, Deploy, Wisdom)

## Cost Tracking

Every step receipt includes: `tokens_in`, `tokens_out`, `model`, `cost_usd`, `cumulative_run_usd`

> Docs: docs/explanation/ATTENTION_ARBITRAGE.md
