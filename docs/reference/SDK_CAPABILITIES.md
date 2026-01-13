# Claude SDK Capabilities in Flow Studio

This document describes which Claude SDK capabilities Flow Studio uses and why certain capabilities are intentionally not used.

## Overview

Flow Studio integrates with the Claude SDK (both `claude_agent_sdk` and legacy `claude_code_sdk` packages) through a transport abstraction layer. Not all SDK capabilities are used - some are intentionally excluded because Flow Studio's architecture provides equivalent functionality through different mechanisms.

## Supported Capabilities

| Capability | Status | Notes |
|------------|--------|-------|
| `output_format` (structured JSON) | Supported | Used for HandoffEnvelope and RoutingSignal extraction in finalize/route phases |
| Pre/Post tool hooks | Supported | Used for foot-gun blocking (dangerous command patterns) and telemetry |
| Interrupts | Supported | Async cancellation during execution |
| Hot context (within step) | Supported | Work -> Finalize -> Route phases share conversation state within a single step |
| Streaming | Supported | Events consumed as they arrive during execution |
| Native tools | Supported | Full Claude Code tool surface (Read, Write, Edit, Bash, Glob, Grep, etc.) |
| Tool observation | Supported | Tool calls visible in event stream for receipt capture |
| Tool interception | Supported | Pre-tool hooks can block dangerous operations |
| Project context | Supported | Loads CLAUDE.md and .claude/ configuration automatically |

## Not Supported (By Design)

| Capability | Status | Rationale |
|------------|--------|-----------|
| File checkpointing (`enable_file_checkpointing`) | Not used | Session amnesia model handles resumability via disk artifacts |
| Rewind (`rewind_files()`) | Not used | Same as above - disk-based checkpoints are preferred |
| Context across steps | Not used | Steps rehydrate from artifacts for auditability |
| Sandbox enforcement | Not used | Settings may be accepted but are not enforced by the adapter |

### Why No SDK Checkpointing?

The Claude SDK supports file checkpointing via `enable_file_checkpointing=True` and `rewind_files(user_message_uuid)`. Flow Studio intentionally does not use these features for three reasons:

1. **Session Amnesia Model**: Flow Studio's architecture is built around the principle that each step starts fresh and rehydrates context from disk artifacts. This is a deliberate design choice documented in the context discipline rules. SDK-level checkpointing would be redundant.

2. **Auditability**: Disk-based receipts (`RUN_BASE/<flow>/receipts/<step>-<agent>.json`) provide a complete audit trail that is independent of SDK state. Every step completion writes a receipt with evidence pointers. This audit trail survives process crashes and can be inspected independently.

3. **Resumability**: The existing checkpoint semantics (receipts + artifacts written to `RUN_BASE/`) enable resumption from any completed step. The kernel can detect the last successful checkpoint and resume from there without relying on SDK state.

If SDK checkpointing is needed in the future, implementation would require:
- Passing `enable_file_checkpointing=True` to `ClaudeAgentOptions`
- Capturing `user_message_uuid` from SDK events
- Calling `sdk.rewind_files(uuid)` to restore file state
- Coordinating with the existing receipt-based checkpoint system

## Package Support

Flow Studio supports both SDK package names for compatibility:

```python
# Preferred (official)
import claude_agent_sdk

# Fallback (legacy)
import claude_code_sdk
```

The import handling is centralized in `swarm/runtime/claude_sdk.py`.

## Transport Capability Matrix

The transport layer declares capabilities via `TransportCapabilities` in `swarm/runtime/transports/port.py`:

| Transport | output_format | hooks | interrupts | hot_context | streaming | native_tools | tool_observation | rewind | sandbox |
|-----------|---------------|-------|------------|-------------|-----------|--------------|------------------|--------|---------|
| Claude SDK | Yes | Yes | Yes | Yes | Yes | Yes | Yes | **No** | No |
| Claude CLI | No | No | No | No | Yes | No | No | No | No |
| Gemini CLI | No | No | No | No | Yes | No | Yes | No | No |
| Stub | Yes | Yes | Yes | Yes | Yes | Yes | Yes | No | No |

Note: `supports_rewind=False` and `supports_sandbox=False` across all transports reflect
the design decision to use disk-based checkpointing and to avoid claiming sandbox enforcement.

## Structured Output Fallback

When `output_format` is not available (CLI transports), the kernel uses fallback strategies:

| Transport | Fallback Strategy |
|-----------|-------------------|
| Claude SDK | `none` (native support) |
| Claude CLI | `best-effort` (parse markdown fences) |
| Gemini CLI | `microloop` (iterate until valid JSON) |
| Stub | `none` (simulates native support) |

## Related Documentation

- [STEPWISE_BACKENDS.md](../STEPWISE_BACKENDS.md) - Stepwise execution configuration
- [resume-protocol.md](../../.claude/rules/execution/resume-protocol.md) - Checkpoint semantics
- [context-discipline.md](../../.claude/rules/execution/context-discipline.md) - Session amnesia model
- [subsumption-principle.md](../../.claude/rules/execution/subsumption-principle.md) - Kernel capability subsumption
