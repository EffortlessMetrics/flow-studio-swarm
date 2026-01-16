# Navigator Protocol

Navigator makes routing decisions when deterministic rules fail.

## Invocation Order
1. Fast-path (no LLM) → If matches, route directly
2. Deterministic checks → If matches, route directly
3. Navigator (LLM) → Only if above fail
4. Escalate → Failure case

## Navigator Input
Compact forensics (not raw data):
- step_completed, agent, status
- forensics: tests, lint, diff, concerns
- iteration: current, max
- previous_failure_signature

## Navigator Output
Bounded decision from closed vocabulary:
- CONTINUE, LOOP, DETOUR, INJECT_FLOW, ESCALATE, TERMINATE

## The Rule
- Navigator routes based on forensics, not narrative
- Decisions are bounded, validated, logged
- When in doubt, escalate—never guess
- Uses economy tier (haiku) for speed

> Docs: docs/execution/ROUTING_PROTOCOL.md
