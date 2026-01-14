# Claude Agent SDK Adapter Contract

This document defines the stable contract for Flow Studio's Claude Agent SDK
adapter. The upstream SDK reference is vendored separately and does not imply
support for every upstream symbol.

## What Flow Studio does with the SDK

Flow Studio orchestrates repeated SDK calls across step-based flows. Each step
is a discrete SDK session (Work -> Finalize -> Route), and flows are sequences
of these steps managed by the orchestrator with persisted handoff artifacts.
Each step is a full multi-turn SDK call scoped to the tools and context needed
for that step.

## Upstream SDK reference (vendored snapshot)

- Snapshot location: `docs/vendor/anthropic/agent-sdk/python/REFERENCE.md`
- Machine-checkable manifests: `VERSION.json`, `API_MANIFEST.json`, `TOOLS_MANIFEST.json`
- Upstream symbols can drift; the adapter contract is the source of truth

## Flow Studio facade (public surface)

Primary entrypoint: `swarm.runtime.claude_sdk`

Guaranteed exports include:

- `StepSessionClient` (per-step Work -> Finalize -> Route)
- `ClaudeSDKClient` (alias of `StepSessionClient`)
- `create_high_trust_options`, `create_options_from_plan`
- `query_with_options`, `query_simple`
- `HANDOFF_ENVELOPE_SCHEMA`, `ROUTING_SIGNAL_SCHEMA`
- `ALL_STANDARD_TOOLS`, `compute_disallowed_tools`, `is_blocked_command`
- `create_dangerous_command_hook`, `create_telemetry_hook`
- `tool`, `create_sdk_mcp_server` (passthrough shims; see below)

## Intentional divergences

- Session model: per-step hot context only; no cross-step session continuity.
- Upstream `query()` exists, but Flow Studio's canonical path is
  `StepSessionClient` and the `query_*` helpers.
- `ClaudeSDKClient` is preserved for compatibility but maps to `StepSessionClient`.

## Not supported or not guaranteed

- `tool()` decorator and `create_sdk_mcp_server()` are exposed as passthrough
  shims only; behavior depends on the installed SDK.
- Message/content-block types and hook matcher/event surfaces are not part of
  the adapter contract.
- Any upstream features not listed above are out of scope until mapped in
  `docs/vendor/anthropic/agent-sdk/python/MAPPING.json`.

## Import boundary

- The SDK is imported only in `swarm/runtime/_claude_sdk/sdk_import.py`.
- All other modules must go through `swarm.runtime.claude_sdk`.
