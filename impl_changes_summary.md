# Implementation Changes Summary

## Component: SpecCompiler Enhancement

**File Changed:** `swarm/spec/compiler.py`

## Summary

Enhanced the SpecCompiler class to support FlowGraph-based compilation with StepPlan output, fragment includes, and deterministic prompt hashing. The implementation follows ADR-001 spec-first architecture and aligns with `prompt_plan.schema.json`.

## Changes Made

### 1. New Data Classes

Added comprehensive data classes for FlowGraph compilation:

- **StepPlan** - Per-step compilation result with:
  - step_id, station_id, system_prompt, user_prompt
  - allowed_tools, permission_mode, max_turns
  - output_schema (JSON schema for structured output)
  - prompt_hash (16-char SHA-256 for reproducibility)
  - verification requirements, fragment references
  - Full `to_dict()` method for serialization

- **FlowNode** - FlowGraph node representation with:
  - node_id, template_id
  - params (parameter substitution)
  - overrides (SDK/station overrides)
  - ui (UI positioning)

- **StepTemplate** - Reusable step template with:
  - id, version, title, station_id
  - objective (ParameterizedObjective)
  - io_overrides, routing_defaults
  - constraints, parameters, tags

- **CompileContext** - Compilation context with:
  - run_id, run_base, repo_root
  - iteration (microloop count)
  - context_pack, scent_trail

- **MultiStepPromptPlan** - Full flow compilation output with:
  - flow_id, steps (List[StepPlan])
  - spec_hash (combined hash)
  - compiled_at timestamp

### 2. New SpecCompiler Methods

**Core Methods:**
- `compile_step(node, template, context)` - Compile FlowNode to StepPlan
- `resolve_template(node, registry)` - Resolve StepTemplate from node
- `build_system_prompt(station, scent_trail)` - Build complete system prompt
- `build_user_prompt(objective, context_pack, io_contract, variables)` - Build user prompt
- `compute_prompt_hash(system, user)` - Compute deterministic 16-char hash

**Multi-Step:**
- `compile_flow(flow_id, context)` - Compile full flow to MultiStepPromptPlan

**Private Helpers:**
- `_resolve_station_id()` - Station ID from node/template
- `_resolve_objective()` - Objective from template + params
- `_build_variables()` - Template substitution variables
- `_build_io_contract()` - Merged IO from station/template/node
- `_build_output_schema()` - JSON schema for handoff
- `_build_verification_from_node()` - Verification requirements
- `_merge_sdk_options()` - SDK options with overrides
- `_process_fragment_includes()` - Process `{{fragment:path}}` syntax
- `_collect_fragment_references()` - Audit trail for fragments
- `_load_template()` - Load StepTemplate from disk (cached)
- `_compile_flow_step()` - Internal FlowStep to StepPlan

### 3. Fragment Include Syntax

Added support for inline fragment includes:
```
{{fragment:common/status_model}}
{{fragment:microloop/critic_never_fixes.md}}
```

The `.md` extension is added automatically if missing. Missing fragments produce a `[Fragment not found: path]` placeholder with a warning log.

### 4. Constants and Presets

- `COMPILER_VERSION = "1.0.0"` - For traceability
- `SYSTEM_PRESETS` - Claude preset content dictionary
- `TOOL_PROFILES` - Quick tool configuration profiles

## Tests Addressed

All 38 existing tests pass:
- TestExtractFlowKey (4 tests)
- TestRenderTemplate (6 tests)
- TestBuildSystemAppend (4 tests)
- TestBuildSystemAppendV2 (2 tests)
- TestBuildUserPrompt (4 tests)
- TestMergeVerificationRequirements (3 tests)
- TestResolveHandoffContract (2 tests)
- TestSpecCompiler (10 tests)
- TestCompilePromptFunction (1 test)
- TestPromptHashComputation (2 tests)

1 test skipped (missing station file - pre-existing issue).

## Trade-offs and Decisions

1. **StepPlan vs PromptPlan**: Added StepPlan as a more complete per-step structure while preserving existing PromptPlan for backward compatibility.

2. **Fragment caching**: Using `@lru_cache` for template loading to avoid repeated disk I/O.

3. **Hash truncation**: 16-character SHA-256 prefix balances uniqueness vs readability.

4. **Context pack format**: `build_user_prompt` accepts dict instead of typed object for flexibility with both existing ContextPack and raw dicts.

5. **Preset handling**: System presets are hardcoded but support custom via `preset_content` attribute.

## Completion State

**VERIFIED** - Code written, all tests pass.

## Files Changed

| File | Change Type |
|------|-------------|
| `swarm/spec/compiler.py` | Enhanced with new methods and data classes |

## Next Steps

1. Add tests for new `compile_step` and `compile_flow` methods
2. Create sample StepTemplate files in `swarm/spec/templates/`
3. Update downstream consumers to use StepPlan where appropriate
