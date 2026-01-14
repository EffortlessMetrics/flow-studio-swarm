# SDK Layer: Operator Guide

Flow Studio vendors a snapshot of the Claude Agent SDK API surface for offline work and drift detection.

## What's Vendored

Located in `docs/vendor/anthropic/agent-sdk/python/`:

| File | Purpose |
|------|---------|
| `VERSION.json` | SDK version metadata (distribution, version, generated timestamp) |
| `API_MANIFEST.json` | Public API surface snapshot (57 exports with signatures and docstrings) |
| `TOOLS_MANIFEST.json` | Tool names extracted from REFERENCE.md |
| `MAPPING.json` | Symbol mapping between SDK and Flow Studio adapter |
| `REFERENCE.md` | Offline SDK documentation snapshot |

These artifacts are **checked in** and validated in CI.

## Drift Detection

### CI (Automatic)

CI runs `make check-vendor-agent-sdk` as part of `make dev-check`. This compares installed SDK against vendored artifacts.

### Manual Check

```bash
# Verify artifacts match installed SDK
uv run python swarm/tools/vendor_agent_sdk.py --check

# Show current state without modifying files
uv run python swarm/tools/vendor_agent_sdk.py --status
```

Drift is detected when:
- Installed SDK version differs from `VERSION.json`
- API exports differ from `API_MANIFEST.json`
- Tool names differ from `TOOLS_MANIFEST.json`

## Facade Guarantees

Flow Studio provides stable imports regardless of SDK version changes.

### Single Import Point

All SDK access goes through `swarm/runtime/_claude_sdk/sdk_import.py`. This module:
- Tries `claude_agent_sdk` first, falls back to `claude_code_sdk`
- Exposes `SDK_AVAILABLE`, `get_sdk_module()`, `get_sdk_version()`

### Stable Public API

Import from `swarm.runtime.claude_sdk`:

```python
from swarm.runtime.claude_sdk import (
    SDK_AVAILABLE,
    create_high_trust_options,
    StepSessionClient,
    ClaudeSDKClient,      # Back-compat alias for StepSessionClient
    ClaudeCodeOptions,    # Back-compat proxy for ClaudeAgentOptions
)
```

### Back-Compat Shims

| Old Name | Maps To | Notes |
|----------|---------|-------|
| `ClaudeSDKClient` | `StepSessionClient` | Alias, same class |
| `ClaudeCodeOptions` | `ClaudeAgentOptions` | Lazy proxy, auto-resolves |

## What's NOT Supported

The adapter layer does **not** expose:

| Feature | Reason |
|---------|--------|
| Rewind/checkpointing | Not exposed by SDK public API |
| Sandbox enforcement | Adapter doesn't enforce; relies on `.claude/settings.json` |
| Full SDK type surface | Only types needed by Flow Studio are shimmed |

For full SDK capabilities, import directly from `claude_agent_sdk` (but lose drift protection).

## Failure Playbook

| Failure Type | Likely Cause | Fix Command |
|--------------|--------------|-------------|
| Drift test fails in CI | SDK updated, artifacts stale | `make vendor-agent-sdk` |
| Facade contract fails | Shim/export missing in adapter | Update `swarm/runtime/claude_sdk.py` |
| Vendor artifact missing | Never generated | `make vendor-agent-sdk` |
| Import error at runtime | SDK not installed | `uv sync --extra dev` |
| Version mismatch warning | SDK upgraded locally | `make vendor-agent-sdk` then commit |

## Commands Reference

| Command | Purpose |
|---------|---------|
| `make vendor-agent-sdk` | Regenerate all vendored artifacts |
| `make check-vendor-agent-sdk` | Verify artifacts match installed SDK (used in CI) |
| `make vendor-agent-sdk-status` | Show current SDK and vendor state |
| `make vendor-help` | Full vendoring documentation |

## Architecture Summary

```
claude_agent_sdk (pip package)
        │
        ▼
swarm/runtime/_claude_sdk/sdk_import.py  ← Single import point
        │
        ▼
swarm/runtime/claude_sdk.py              ← Public facade + shims
        │
        ▼
Flow Studio runtime (orchestrator, receipts, etc.)
```

## See Also

- `docs/vendor/anthropic/agent-sdk/python/` - Vendored artifacts
- `swarm/tools/vendor_agent_sdk.py` - Vendoring script
- `swarm/runtime/_claude_sdk/` - Internal SDK adapter modules
