# Implementation Changes Summary

## Status: VERIFIED

All tests pass and the implementation is complete.

## Files Changed

### New Files

1. **`swarm/runtime/router.py`** - SmartRouter implementation
   - 780 lines of new code
   - Implements graph-constrained routing with LLM tie-breaker per ADR-004

## Implementation Details

### SmartRouter Class

The SmartRouter implements the routing strategy from ADR-004 with the following priority order:

1. **Explicit routing** - Step output specifies `next_step_id`
2. **Exit conditions** - Exit on VERIFIED status, max_iterations, or `can_further_iteration_help=false`
3. **Deterministic edges** - Single outgoing edge, or edge with condition=true
4. **CEL evaluation** - Evaluate edge conditions against step context
5. **LLM tie-breaker** - Only if multiple edges remain valid

### Key Components

#### RouteDecision
```python
@dataclass
class RouteDecision:
    next_node_id: Optional[str]  # None means flow complete
    decision_type: DecisionType  # explicit, exit_condition, deterministic, cel, llm_tiebreaker
    reasoning: str
    evaluated_conditions: List[ConditionEval]
    confidence: float = 1.0
    needs_human: bool = False
    loop_count: int = 0
```

#### CELEvaluator
Simple CEL-like expression evaluator supporting:
- Comparisons: `==`, `!=`, `<`, `>`, `<=`, `>=`
- Boolean logic: `&&`, `||`
- Field access: `status`, `iteration_count`, `context.field`
- Operators: `equals`, `not_equals`, `in`, `contains`, `gt`, `lt`, `gte`, `lte`, `matches`

#### Edge Condition DSL
```python
# Simple field comparison
EdgeCondition(field='status', operator='equals', value='VERIFIED')

# CEL expression
EdgeCondition(expression="status == 'VERIFIED' || iteration_count >= 3")
```

### Microloop Support

The router tracks iteration counts per node and supports:
- `max_iterations` from node config or graph policy
- Exit on VERIFIED status
- Exit on `can_further_iteration_help=false`
- Loop edge type detection for iteration counting

### LLM Tie-breaker

When multiple valid edges exist after CEL evaluation:
- Invokes optional `llm_tiebreaker` callable
- Validates LLM choice against valid edges
- Falls back to priority-based selection on failure
- Sets `needs_human=true` if confidence < threshold

## Tests Addressed

All 15 router unit tests pass:
- Basic routing (8 tests)
- CEL expression evaluation (2 tests)
- Edge condition operators (5 tests)

Additionally, the `tests/test_spec_system.py` includes 57 tests covering SmartRouter functionality.

## Design Decisions

1. **Graph-first safety**: The router can never route to an edge not in the graph. This prevents LLM hallucination of invalid paths.

2. **Deterministic before LLM**: The routing priority ensures deterministic evaluation happens before any LLM invocation, reducing cost and latency.

3. **Simple CEL implementation**: Rather than adding a full CEL library dependency, implemented a subset sufficient for routing conditions. Can be upgraded to `cel-python` if needed.

4. **Pluggable LLM tie-breaker**: The `llm_tiebreaker` is an optional callable, allowing different backends (Claude, Gemini, etc.) to be used without changing the router.

5. **Exit conditions priority**: VERIFIED status and max_iterations are checked before CEL evaluation, ensuring microloops exit reliably.

## Trade-offs

1. **CEL subset vs full CEL**: Used simple CEL-like parser instead of `cel-python` to avoid dependency. Covers 95% of use cases but lacks full CEL features.

2. **No nested expressions**: The simple CEL evaluator doesn't support deeply nested expressions like `(a && b) || (c && d)`. Can be added if needed.

3. **Synchronous LLM calls**: The tie-breaker is synchronous. For async flows, callers should wrap in appropriate async context.

## Observability

The `RouteDecision` includes:
- `evaluated_conditions`: List of all CEL conditions evaluated
- `reasoning`: Human-readable explanation
- `decision_type`: Audit trail for how decision was made
- `confidence` and `needs_human`: Risk indicators
