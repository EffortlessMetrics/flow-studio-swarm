# Vendoring the Claude Agent SDK Reference

Flow Studio vendors a snapshot of the Claude Agent SDK API surface so agents and reviewers can work offline.

## What's Vendored

```
docs/vendor/anthropic/agent-sdk/python/
  REFERENCE.md        # Human-readable SDK reference (optional, hand-maintained)
  VERSION.json        # SDK package metadata (generated)
  API_MANIFEST.json   # Introspected API surface (generated)
  TOOLS_MANIFEST.json # Tool names from REFERENCE.md (generated)
```

### Artifact Descriptions

| File | Purpose | Update Trigger |
|------|---------|----------------|
| `VERSION.json` | SDK version, module name, distribution | SDK version change |
| `API_MANIFEST.json` | Public exports, signatures, methods | SDK API change |
| `TOOLS_MANIFEST.json` | Tool names from reference docs | REFERENCE.md change |
| `REFERENCE.md` | Human-readable SDK documentation | Upstream doc change |

## Update Procedure

### 1. When SDK Version Changes

After updating the SDK dependency:

```bash
# Update SDK
pip install -U claude-agent-sdk

# Regenerate vendor artifacts
make vendor-agent-sdk

# Verify
make check-vendor-agent-sdk

# Commit
git add docs/vendor/anthropic/agent-sdk/python/
git commit -m "chore: update vendored SDK artifacts for vX.Y.Z"
```

### 2. When Upstream Docs Change

If Anthropic updates the SDK documentation:

1. Update `docs/vendor/anthropic/agent-sdk/python/REFERENCE.md` with new content
2. Run `make vendor-agent-sdk` to regenerate TOOLS_MANIFEST.json
3. Commit both files

### 3. Routine Verification

Check that vendored artifacts match the installed SDK:

```bash
make check-vendor-agent-sdk
```

This returns:
- Exit 0: Artifacts are current
- Exit 1: Drift detected, run `make vendor-agent-sdk`
- Exit 2: Missing files, run `make vendor-agent-sdk`

## CI Enforcement

Add to your CI pipeline:

```yaml
- name: Check SDK vendor drift
  run: make check-vendor-agent-sdk
```

This catches:
- SDK updates without vendor refresh
- Accidental edits to generated files
- Missing vendor files after clone

## What Agents Can Check Offline

With vendored artifacts, agents can:

### 1. Verify SDK is Available

```python
from pathlib import Path
import json

vendor_dir = Path("docs/vendor/anthropic/agent-sdk/python")
version_file = vendor_dir / "VERSION.json"

if version_file.exists():
    data = json.loads(version_file.read_text())
    print(f"SDK: {data['import_module']} v{data['version']}")
```

### 2. Check API Surface

```python
api_file = vendor_dir / "API_MANIFEST.json"
api = json.loads(api_file.read_text())

# What's exported?
exports = api["exported"]
print(f"Exports: {list(exports.keys())}")

# Does ClaudeCodeOptions exist?
if "ClaudeCodeOptions" in exports:
    print("ClaudeCodeOptions available")
```

### 3. Verify Tool Names

```python
tools_file = vendor_dir / "TOOLS_MANIFEST.json"
tools = json.loads(tools_file.read_text())

# What tools are documented?
tool_names = tools["tool_names"]
print(f"Documented tools: {tool_names}")
```

## Contract Tests

The vendored artifacts are validated by contract tests:

```bash
uv run pytest tests/contract/test_vendor_agent_sdk.py -v
```

These tests verify:
- Vendor files exist and are valid JSON
- Required SDK symbols are in API_MANIFEST
- Tool names are extractable from reference

## The Philosophy

### Why Vendor?

1. **Offline Capability** - Agents work without network access
2. **Drift Detection** - Catch SDK/adapter misalignment early
3. **Audit Trail** - Git history shows SDK evolution
4. **Contract Testing** - Validate assumptions without live SDK

### What NOT to Vendor

- **Full upstream prose** - License/terms risk, staleness
- **Test fixtures** - Generate from installed SDK
- **Implementation details** - Only public API surface

### Single Source of Truth

The **installed SDK** is truth. Vendored artifacts are a snapshot for:
- Offline reference
- Drift detection
- Contract testing

When drift is detected, update the vendor snapshot - don't edit it manually.

## Commands Reference

| Command | Purpose |
|---------|---------|
| `make vendor-agent-sdk` | Generate/update vendor artifacts |
| `make check-vendor-agent-sdk` | Verify artifacts match installed SDK |
| `make vendor-agent-sdk-status` | Show SDK and vendor status |
| `make vendor-help` | Show vendoring commands and workflow |

## Troubleshooting

### "SDK not installed"

```bash
# Install the official package
pip install claude-agent-sdk

# Or the legacy package
pip install claude-code-sdk
```

### "Missing vendored files"

```bash
# Generate the vendor artifacts
make vendor-agent-sdk
```

### "Drift detected"

```bash
# Regenerate and commit
make vendor-agent-sdk
git add docs/vendor/anthropic/agent-sdk/python/
git commit -m "chore: refresh vendored SDK artifacts"
```

### "REFERENCE.md missing"

REFERENCE.md is optional but enables tool name extraction. Create it by:
1. Copying upstream SDK documentation
2. Using the format with `**Tool name:** \`ToolName\`` for tool listings

## See Also

- [docs/AGENT_SDK_INTEGRATION.md](../AGENT_SDK_INTEGRATION.md) - SDK integration guide
- [docs/reference/SDK_CAPABILITIES.md](SDK_CAPABILITIES.md) - Capability matrix
- [tests/contract/test_sdk_contract.py](../../tests/contract/test_sdk_contract.py) - SDK contract tests
- [tests/contract/test_vendor_agent_sdk.py](../../tests/contract/test_vendor_agent_sdk.py) - Vendor contract tests
