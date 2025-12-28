# Implementation Changes Summary

## Task
Wire SpecAdapter into ClaudeStepEngine.run_worker()

## Files Changed

### `swarm/runtime/engines/claude/engine.py`

**Changes Made:**

1. **Added import for `try_compile_from_spec`** (line 74):
   ```python
   from .spec_adapter import try_compile_from_spec
   ```

2. **Modified `_run_worker_async()` method** (lines 941-961):
   - Added spec-based prompt compilation attempt BEFORE legacy `build_prompt()` call
   - When spec compilation succeeds:
     - Uses `plan.user_prompt` as the query prompt
     - Uses `plan.system_append` as the agent persona for SDK options
     - Logs the `plan.prompt_hash`, `plan.station_id`, and `plan.station_version` for traceability
   - When spec compilation returns `None`:
     - Falls back to existing `build_prompt()` path
     - Logs that legacy prompt builder is being used

## Implementation Details

The integration follows a **spec-first, legacy-fallback** pattern:

```python
# Try spec-based prompt compilation first, fall back to legacy
spec_result = try_compile_from_spec(ctx, self.repo_root)

if spec_result:
    # Use spec-based prompts
    prompt, agent_persona, plan = spec_result
    logger.debug(
        "Using spec-based prompt for step %s (hash=%s, station=%s v%d)",
        ctx.step_id,
        plan.prompt_hash,
        plan.station_id,
        plan.station_version,
    )
    truncation_info = None  # Spec compilation handles context management
else:
    # Fall back to legacy prompt builder
    logger.debug(
        "Spec not available for step %s, using legacy prompt builder",
        ctx.step_id,
    )
    prompt, truncation_info, agent_persona = self._build_prompt(ctx)
```

## Tests Addressed

All existing tests pass:
- 8 engine hydration tests (test_claude_engine_hydration.py)
- 15 prompt builder tests (test_prompt_builder.py)

## Trade-offs and Decisions

1. **Spec-first approach**: The integration attempts spec-based compilation first, ensuring new spec-driven flows take precedence when available.

2. **Backward compatibility**: The legacy `build_prompt()` path remains fully functional for flows without spec definitions.

3. **Context management**: When using specs, `truncation_info` is set to `None` since spec compilation handles context budgets internally.

4. **Traceability logging**: Added debug logging with prompt hash and station version for auditability.

5. **Minimal change surface**: Only two edits were made to the engine file:
   - One import statement
   - One conditional block before prompt building

## Critique Issues Resolved

N/A - No code_critique.md was present.

## Verification Status

**VERIFIED** - All tests pass, backward compatibility maintained.
