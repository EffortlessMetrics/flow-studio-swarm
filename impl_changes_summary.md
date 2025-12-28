# Implementation Changes Summary

## Task
Integrate spec-first routing into the orchestrator at `swarm/runtime/orchestrator.py`.

## Files Changed

### 1. `swarm/runtime/orchestrator.py`

Major enhancements for spec-first routing:

#### New Imports
- Added `re`, `subprocess` for verification command execution
- Added conditional import for `swarm.spec.loader` (load_flow, load_station)
- Added `SPEC_AVAILABLE` flag for graceful degradation

#### New Class Attributes
- `_flow_spec_cache: Dict[str, Any]` - Cache for loaded FlowSpecs
- `_station_spec_cache: Dict[str, Any]` - Cache for loaded StationSpecs

#### New Methods: Spec-First Routing Support

1. **`_load_flow_spec(flow_key)`**: Load FlowSpec with caching
   - Maps flow keys to spec IDs (e.g., "build" -> "3-build")
   - Caches results to avoid repeated file I/O
   - Returns None if spec not available (graceful degradation)

2. **`_load_station_spec(station_id)`**: Load StationSpec with caching
   - Loads station specs for verification
   - Caches results for performance
   - Returns None if spec not available

3. **`_get_macro_routing(flow_key, success)`**: Get macro-routing from FlowSpec
   - Checks `on_complete.next_flow` when flow succeeds
   - Checks `on_failure.next_flow` when flow fails
   - Returns (next_flow_key, reason) tuple

4. **`_get_spec_step_routing(flow_key, step_id)`**: Get step routing from FlowSpec
   - Returns routing configuration dict from FlowSpec step
   - Includes: kind, next, loop_target, exit_on conditions, max_iterations, branches

#### New Methods: Verification Execution

5. **`_run_verification(run_id, flow_key, step_id, station_id, envelope)`**: Run verification checks
   - Emits `verification_started` event
   - Checks `required_artifacts` from station verify block
   - Runs `verification_commands` (shell commands with success patterns)
   - Skips skill-based commands (test-runner, auto-linter, policy-runner)
   - Emits `verification_passed` or `verification_failed` event
   - Returns verification results with gate_status_on_fail

#### New Methods: Spec-First Routing Signal

6. **`_create_routing_signal_from_spec(step, result, loop_state, spec_routing)`**: Create routing signal from FlowSpec
   - Supports routing kinds: linear, microloop, branch, terminal
   - Handles exit_on conditions for microloops:
     - Status values (e.g., ["VERIFIED", "verified"])
     - can_further_iteration_help: false
   - Tracks loop_count and exit_condition_met
   - Returns RoutingSignal with spec-sourced decision

7. **`_get_spec_exit_on(flow_key, step_id)`**: Get exit_on conditions from FlowSpec
   - Reads raw YAML to get exit_on block from step routing
   - Returns dict with status values and can_further_iteration_help

#### Updated Methods

8. **`_create_routing_signal()`**: Now uses spec-first routing
   - Tries `_get_spec_step_routing()` first
   - If spec found, delegates to `_create_routing_signal_from_spec()`
   - Falls back to config-based routing if no spec

9. **`_execute_stepwise()`**: Added verification and macro-routing
   - After step execution, gets station_id from FlowSpec
   - Calls `_run_verification()` for station verification
   - Updates handoff envelope with verification results:
     - `verification_passed: bool`
     - `verification_details: Dict` (artifact_checks, command_checks)
     - `station_id: str`
   - After flow completes, calls `_get_macro_routing()`
   - Emits `macro_route` event if next flow is defined
   - Updates `run_state.flow_transition_history`
   - Includes macro-routing info in `run_completed` event

## New Event Types Emitted

1. **`verification_started`**: When step verification begins
   - Payload: station_id

2. **`verification_passed`**: When verification succeeds
   - Payload: station_id, artifact_checks, command_checks, reason

3. **`verification_failed`**: When verification fails
   - Payload: station_id, gate_status_on_fail, artifact_checks, command_checks

4. **`macro_route`**: When flow completes with defined next_flow
   - Payload: from_flow, to_flow, reason, flow_succeeded, loop_count

## Flow Context Tracking

In `run_completed` event:
- `next_flow`: Next flow from macro-routing (or None)
- `macro_route_reason`: Reason for flow transition
- `flow_transition_history`: List of all flow transitions in run

In `RunState`:
- `current_flow_index`: 1-based index of current flow
- `flow_transition_history`: Ordered list of flow transitions with metadata

## Tests Addressed

### Verified Working
- Spec loader tests: 46/48 passing
- FlowSpec loading: Works correctly (tested manually)
- RoutingKind.TERMINAL: Recognized from spec

### Known Issue (Pre-existing)
- Circular import in swarm.runtime module prevents direct import of orchestrator
- This is a pre-existing issue in the codebase (not introduced by this change)
- The circular import is: context_pack.py -> engines -> claude/engine.py -> context_pack.py

## Trade-offs and Decisions

1. **Graceful Degradation**: SPEC_AVAILABLE flag allows orchestrator to work without spec module. Falls back to config-based routing.

2. **YAML Parsing for exit_on**: FlowSpec dataclass doesn't include exit_on, so we read raw YAML. This is temporary until spec types are extended.

3. **Skill Commands Skipped**: Verification commands like "test-runner" are skipped since they require skill runner integration.

4. **Station ID from FlowSpec**: We get station_id from FlowSpec step, not from agent/config, for traceability.

5. **Flow ID Mapping**: Hardcoded map from flow_key to flow_id (e.g., "build" -> "3-build"). Could be derived from flow_registry.

## Critique Issues Resolved

N/A - No code_critique.md was present.

## Verification Status

**UNVERIFIED** - Code written, but tests cannot run due to pre-existing circular import issue in swarm.runtime module. The spec loader tests pass (46/48), and manual testing confirms FlowSpec loading works correctly.

### Blocking Issue

The orchestrator cannot be imported due to a circular import:
```
orchestrator.py -> context_pack.py -> engines -> claude/engine.py -> context_pack.py
```

This is a pre-existing architectural issue that needs to be resolved separately. The new code follows the existing patterns and does not introduce new circular dependencies.
