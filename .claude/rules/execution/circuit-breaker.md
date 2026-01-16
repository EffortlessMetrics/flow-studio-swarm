# Circuit Breaker

After repeated failures, stop trying.

## State Machine
- CLOSED (normal) → 3 failures → OPEN (paused 30s)
- OPEN → 30s → HALF-OPEN (try one)
- HALF-OPEN → success → CLOSED
- HALF-OPEN → failure → OPEN
- 5 total failures → ESCALATE

## The Rule
One success resets. Give failing services room to recover.

> Docs: docs/execution/ERROR_HANDLING.md
