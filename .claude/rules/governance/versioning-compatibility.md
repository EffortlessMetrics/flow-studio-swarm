# Versioning Compatibility

Compatibility guarantees define what changes are safe and what requires migration.

## Compatibility Levels

### PATCH (x.x.N)
- Bug fixes only
- No behavioral changes
- Fully backward compatible
- No migration required

### MINOR (x.N.0)
- New optional fields
- New enum values (additive)
- Backward compatible
- Old artifacts readable without modification

### MAJOR (N.0.0)
- Breaking changes
- Migration required
- Support N-1 minimum
- Document migration path

## Breaking Changes (Require MAJOR Bump)

| Change Type | Example | Why Breaking |
|-------------|---------|--------------|
| Remove required field | Drop `step_id` from receipt | Old readers expect it |
| Change field type | `tokens: number` to `tokens: object` | Parsing fails |
| Rename field | `started_at` to `start_time` | Old readers miss it |
| Change step order | Swap steps 2 and 3 | Flow execution differs |
| Change agent contract | Critic now fixes code | Behavioral change |
| Remove enum value | Drop `BLOCKED` status | Validation fails |

## Non-Breaking Changes (MINOR or PATCH)

| Change Type | Version | Example |
|-------------|---------|---------|
| Add optional field | MINOR | Add `workspace_root` |
| Add new enum value | MINOR | Add `DETOUR` to routing |
| Add new agent | MINOR | Add `lint-fixer` agent |
| Add new flow | MINOR | Add Flow 8 (Reset) |
| Improve prompt wording | PATCH | Clarify critic instructions |
| Fix typo in schema | PATCH | Fix `comletion` to `completion` |
| Add validation | PATCH | Require positive token counts |

## Version in Artifacts

### Receipts

```json
{
  "schema_version": "1.2.0",
  "engine": "claude-step",
  "step_id": "build-step-3",
  ...
}
```

### Handoff Envelopes

```json
{
  "schema_version": "2.0.0",
  "meta": { ... },
  "status": "VERIFIED",
  ...
}
```

### Flow Definitions

```yaml
flow_version: 2024-01-15
flow_key: build
steps:
  - id: step-1
    ...
```

## Anti-Patterns

### Silent Breaking Changes
```
# BAD: Changed field type without version bump
tokens: 500  # Was number, now sometimes string
```

### Version Inflation
```
# BAD: MAJOR bump for adding optional field
schema_version: 5.0.0  # Was 4.0.0, only added optional field
```

## Enforcement

### Validation

`validate_swarm.py` checks:
1. Schema versions are valid semver
2. Flow versions are valid dates
3. Referenced versions exist
4. No unsupported versions in active runs

### CI Checks

- Block MAJOR bumps without migration script
- Warn on deprecated version usage
- Track version distribution in runs

## The Rule

> Breaking changes require MAJOR bump.
> Additive changes are MINOR.
> Bug fixes are PATCH.
> When in doubt, it's breaking.

---

## See Also
- [versioning-schemes.md](./versioning-schemes.md) - What versioning scheme to use
- [versioning-migration.md](./versioning-migration.md) - How to migrate between versions
- [deprecation-stages.md](./deprecation-stages.md) - Sunset process for agents and flows
