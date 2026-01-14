# Deprecation Migration

## Purpose

Defines migration requirements, documentation standards, and tracking for deprecated items. Ensures users have clear paths forward when features sunset.

## The Rule

> Every deprecation has a migration guide. Tooling should be idempotent.
> Warnings appear everywhere users interact with the system.

## Documentation Requirements

Every deprecated item must have a migration guide:
```
docs/migration/<old-item>-to-<new-item>.md
```

**Required contents:**
1. **Summary**: One paragraph on what's changing
2. **Timeline**: When each stage happens
3. **Migration steps**: Numbered, actionable instructions
4. **Mapping table**: Old -> New for all fields/parameters
5. **Edge cases**: Known issues and workarounds
6. **Rollback**: How to undo if needed
7. **Support**: Where to get help

## Automated Migration

Where feasible, provide tooling:

```bash
# Example: Agent migration
make migrate-agent FROM=old-agent TO=new-agent

# Example: Schema migration
make migrate-schema FROM=v1 TO=v2 DATA_PATH=swarm/runs/
```

**Tooling requirements:**
- Be idempotent (safe to run multiple times)
- Produce detailed logs
- Have dry-run mode
- Handle partial failures gracefully

## Warning Integration

Warnings must appear in:
- CLI output (if applicable)
- Log files
- Validation output (`make validate-swarm`)
- Documentation (deprecation badges)

## Validation

Pack-check validates deprecation compliance:

```python
def validate_deprecation(item):
    if item.deprecated:
        assert item.deprecated.since, "Deprecation must have 'since' version"
        assert item.deprecated.alternative, "Deprecation must have alternative"
        assert item.deprecated.removal_target, "Deprecation must have removal target"
        assert migration_guide_exists(item), "Migration guide required"
```

## Tracking Deprecations

Maintain a deprecation registry:

```yaml
# specs/deprecations.yaml
deprecations:
  - item: old-agent
    type: agent
    since: v2.5.0
    stage: migration
    alternative: new-agent
    removal_target: v3.0.0
    migration_guide: docs/migration/old-agent-to-new-agent.md

  - item: v1-receipt-schema
    type: schema
    since: v2.4.0
    stage: disabled
    alternative: v2-receipt-schema
    removal_target: v2.8.0
    migration_guide: docs/migration/receipt-schema-v1-to-v2.md
```

This enables:
- Automated deprecation status checks
- Release note generation
- Migration progress tracking

## Anti-Patterns

### Silent Removal

```bash
# BAD: Just delete it
git rm swarm/agents/old-agent.md
git commit -m "Remove old agent"
```

**Problem:** External users break without warning.

### Deprecation Without Alternative

```yaml
# BAD: No path forward
deprecated:
  since: "v2.5.0"
  reason: "No longer needed"
  # Missing: alternative
```

**Problem:** Users don't know what to do instead.

### Rushed Timeline

```
v2.5.0: Marked
v2.5.1: Removed  # BAD: No migration window
```

**Problem:** Users have no time to adapt.

### Warning Without Action

```yaml
# BAD: Warn forever, never remove
deprecated:
  since: "v1.0.0"  # Three years ago
  removal_target: null
```

**Problem:** Deprecation warnings become noise.

---

## See Also

- [deprecation-stages.md](./deprecation-stages.md) - The four-stage lifecycle
- [versioning-migration.md](./versioning-migration.md) - Reading old artifacts
- [capability-registry.md](../artifacts/capability-registry.md) - Evidence for capabilities
- [agent-behavioral-contracts.md](./agent-behavioral-contracts.md) - Agent definitions
