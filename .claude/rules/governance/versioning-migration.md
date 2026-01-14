# Versioning Migration

How to read old artifacts and migrate between versions.

## Reading Old Artifacts

The system MUST support reading N-1 version minimum.

### Version Detection

```python
def detect_version(artifact):
    if 'schema_version' in artifact:
        return artifact['schema_version']
    # Legacy: no version field = 1.0.0
    return '1.0.0'
```

### Version-Aware Parsing

```python
def parse_receipt(data):
    version = detect_version(data)

    if version.startswith('1.'):
        return parse_v1_receipt(data)
    elif version.startswith('2.'):
        return parse_v2_receipt(data)
    else:
        raise UnsupportedVersion(version)
```

## Migration Support

### MAJOR Version Migrations

When bumping MAJOR version:

1. **Document breaking changes** in changelog
2. **Provide migration script** for artifacts
3. **Support N-1 for reading** (at minimum)
4. **Deprecate N-2** with warning
5. **Remove N-3** support

### Migration Script Location

```
swarm/migrations/
├── receipt_v1_to_v2.py
├── handoff_v1_to_v2.py
└── README.md
```

### Migration Example

```python
def migrate_receipt_v1_to_v2(v1_receipt):
    """Migrate receipt from v1.x to v2.x format."""
    return {
        'schema_version': '2.0.0',
        'step_id': v1_receipt['step_id'],
        'tokens': {
            'prompt': v1_receipt.get('prompt_tokens', 0),
            'completion': v1_receipt.get('completion_tokens', 0),
            'total': v1_receipt.get('total_tokens', 0),
        },
        ...
    }
```

## Deprecation Policy

| Phase | Duration | Behavior |
|-------|----------|----------|
| Current | N/A | Full support |
| Deprecated | 2 releases | Warning on read, still functional |
| Removed | After deprecated | Error on read |

### Deprecation Warning

```python
if version < MIN_SUPPORTED_VERSION:
    warn(f"Receipt version {version} is deprecated. Migrate to {CURRENT_VERSION}.")
```

## Anti-Patterns

### No Migration Path
```
# BAD: Breaking change with no migration script
ERROR: Cannot read receipt v1.0.0 (unsupported)
```

### Forgetting Legacy Artifacts
```
# BAD: Old runs become unreadable
swarm/runs/2024-01-01/  # Cannot parse receipts
```

## The Rule

> Version everything that can break readers.
> Support N-1 minimum.
> Migration is mandatory for MAJOR bumps.

---

## See Also
- [versioning-schemes.md](./versioning-schemes.md) - What versioning scheme to use
- [versioning-compatibility.md](./versioning-compatibility.md) - What breaks vs what's safe
- [deprecation-stages.md](./deprecation-stages.md) - Full deprecation lifecycle
- [receipt-schema.md](../artifacts/receipt-schema.md) - Current receipt format
- [handoff-protocol.md](../artifacts/handoff-protocol.md) - Envelope structure
