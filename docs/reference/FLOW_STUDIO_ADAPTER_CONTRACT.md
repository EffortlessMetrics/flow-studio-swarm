# Flow Studio Adapter Contract

This document defines the stable contract for the Flow Studio Claude SDK
adapter (`swarm.runtime.claude_sdk`). It is the canonical offline reference for
what Flow Studio guarantees, independent of upstream SDK changes.

## Scope and guarantees

Flow Studio treats the adapter as the contract surface. The upstream SDK is a
dependency that can drift. We guarantee:

- A stable adapter facade in `swarm.runtime.claude_sdk`.
- Deterministic option building and tool restriction helpers.
- Stable schemas for handoff and routing.
- Explicit capability declarations for each transport.

We do not guarantee upstream symbols or behavior beyond what is recorded in the
vendored artifacts (see "Vendoring and drift").

## StepSessionClient and hot context

`StepSessionClient` is the per-step session orchestrator. It runs the three
phases in sequence inside a single session:

1. Work - the agent executes the task with tools enabled.
2. Finalize - structured handoff extraction.
3. Route - routing decision for the next step.

Hot context is preserved within a step (Work -> Finalize -> Route). Across
steps, Flow Studio uses session amnesia by design: each step rehydrates context
from disk artifacts (receipts, transcripts, handoff envelopes).

## Structured output guarantees

Flow Studio always uses the same handoff and routing schemas:

- `HANDOFF_ENVELOPE_SCHEMA`
- `ROUTING_SIGNAL_SCHEMA`

When the transport supports native structured output (`output_format`), we use
schema validation directly. When it does not, we fall back to:

- Best-effort JSON fence parsing (Claude CLI).
- Microloop extraction (Gemini CLI).

The goal is consistent schemas regardless of transport, with explicit fallback
behavior declared in transport capabilities.

## Tool restriction semantics

Tool restriction is deterministic:

- `allowed_tools` defines what is permitted.
- `disallowed_tools` is computed as the complement of `allowed_tools` against
  `ALL_STANDARD_TOOLS` via `compute_disallowed_tools`.

This is paired with a high-trust policy that allows broad access while blocking
obvious foot-guns (for example, `rm -rf /` or `git push --force`). Enforcement
of `disallowed_tools` depends on upstream SDK behavior, so the adapter treats it
as a best-effort contract and documents the limitation in tests.

## Hooks and telemetry

The adapter supports pre and post tool hooks for guardrails and telemetry. Hook
types are re-exported as shims when the SDK is present, but the adapter only
promises behavior for the hooks it uses (PreToolUse and PostToolUse).

## Unsupported or not enforced

These capabilities are explicitly not supported by the adapter today:

- Rewind/checkpointing (`supports_rewind` is False).
- Sandbox enforcement (settings are accepted but not enforced unless SDK
  support exists and is covered by a contract test).
- Cross-step hot context (`supports_context_across_steps` is False).

If any of these change, the contract and capability registry must be updated
with evidence.

## Vendoring and drift

Vendored artifacts live in `docs/vendor/anthropic/agent-sdk/python/`:

- `VERSION.json` - SDK package metadata.
- `API_MANIFEST.json` - SDK API surface snapshot.
- `TOOLS_MANIFEST.json` - Tool names extracted from REFERENCE.md.
- `REFERENCE.md` - Human-readable SDK reference.
- `MAPPING.json` - Symbol support mapping for the adapter.

Update workflow:

1. Update the SDK (for example, `uv sync --extra dev`).
2. Update `REFERENCE.md` if upstream docs changed.
3. Run `make vendor-agent-sdk`.
4. Commit updated artifacts.

CI and `make dev-check` run `make check-vendor-agent-sdk` to detect drift.

## Receipts and debugging

Step receipts record which SDK powered a run:

- `sdk_module`
- `sdk_distribution`
- `sdk_version`

This makes mismatches between local and CI environments easy to diagnose.
