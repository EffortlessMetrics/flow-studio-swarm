# Deprecation Stages

## Purpose

Defines the four-stage deprecation lifecycle and what requires the formal deprecation process versus what can be removed directly.

## The Rule

> External dependents get warning. Internal cleanup is encouraged.
> Two releases minimum from migration to disabled. One release from disabled to removed.

## The Four Stages

### Stage 1: Marked

The item is flagged for deprecation but remains fully functional.

**Actions:**
- Add `@deprecated` tag to definition
- Add deprecation notice to documentation
- Log warnings on every use
- Document why it's being deprecated

**Marker format:**
```yaml
deprecated:
  since: "v2.5.0"
  reason: "Superseded by new-agent with better coverage"
  alternative: "new-agent"
  removal_target: "v3.0.0"
```

**Log format:**
```
[DEPRECATION WARNING] Agent 'old-agent' is deprecated since v2.5.0.
  Use 'new-agent' instead. Removal planned for v3.0.0.
  See: docs/migration/old-agent-to-new-agent.md
```

### Stage 2: Migration

Alternative is documented and migration path is clear.

**Requirements:**
- Migration guide exists
- Alternative is production-ready
- Automated migration tooling (where feasible)
- Warnings escalate to prominent notices

### Stage 3: Disabled

Using the deprecated item produces errors, but code remains.

**Actions:**
- Use triggers error with migration pointer
- Code remains in place (rollback possible)
- Metrics track attempted usage
- Support window for stragglers

**Error format:**
```
[DEPRECATION ERROR] Agent 'old-agent' is disabled as of v3.0.0.
  This agent no longer functions. Migrate to 'new-agent'.
  See: docs/migration/old-agent-to-new-agent.md
  If you cannot migrate, contact support before v3.1.0.
```

### Stage 4: Removed

Code is deleted from the codebase.

**Actions:**
- Delete implementation
- Delete tests (archive if historically interesting)
- Update documentation to remove references
- Add to CHANGELOG as breaking change

## Timeline Requirements

| Transition | Minimum Duration | Rationale |
|------------|------------------|-----------|
| Marked -> Migration | Immediate | Documentation is a prerequisite |
| Migration -> Disabled | 2 releases | Users need time to migrate |
| Disabled -> Removed | 1 release | Final warning period |

**Example timeline:**
```
v2.5.0: Marked (warnings start)
v2.5.0: Migration (guide published same release)
v2.7.0: Disabled (errors, 2 releases later)
v2.8.0: Removed (code deleted, 1 release later)
```

## What Requires Deprecation Process

### Agents

Agents may have:
- External tooling that invokes them
- Flow configurations that reference them
- Scripts that depend on their output format

**Deprecation required:** Always

### Flows

Flows may have:
- CI/CD integrations
- Monitoring dashboards
- External orchestration dependencies

**Deprecation required:** Always

### Artifact Schemas

Schemas may have:
- Stored data in existing format
- Downstream consumers parsing output
- Integration contracts with external systems

**Deprecation required:** Always
**Additional requirement:** Schema migration tooling for stored data

### Public APIs/Contracts

APIs may have:
- External consumers
- Integration partners
- Documented contracts

**Deprecation required:** Always
**Additional requirement:** Versioned API support during migration

## What Can Be Removed Directly

### Internal Implementation Details

Code that:
- Is not exposed in any public interface
- Has no external references
- Is purely internal optimization

**Deprecation required:** No
**Best practice:** Comment in PR why no deprecation needed

### Unused Code with No References

Code that:
- Is never invoked
- Has no configuration references
- Is not documented as a feature

**Deprecation required:** No
**Best practice:** Verify with grep/search before removal

### Failed Experiments

Code that:
- Was never shipped to users
- Exists only in development branches
- Has no external documentation

**Deprecation required:** No
**Best practice:** Document the experiment's learnings before deletion

---

## See Also

- [deprecation-migration.md](./deprecation-migration.md) - Migration requirements and tracking
- [versioning-compatibility.md](./versioning-compatibility.md) - What breaks vs what's safe
- [pack-check-philosophy.md](./pack-check-philosophy.md) - Validation philosophy
