# Versioning Schemes

**"If you can't read yesterday's receipts, yesterday's work is lost."**

Different artifacts use different versioning schemes based on their nature and change patterns.

## What Gets Versioned

| Artifact Type | What Changes | Impact |
|---------------|--------------|--------|
| **Schemas** | Receipt, handoff, envelope formats | Breaks artifact parsing |
| **Flows** | Step structure, agent assignments | Breaks flow execution |
| **Agents** | Behavioral changes in prompts | Changes work output |
| **Configs** | YAML structures, registry formats | Breaks tooling |

## Schemas: Semantic Versioning (MAJOR.MINOR.PATCH)

```
receipt_schema: 1.2.0
handoff_schema: 2.0.1
envelope_schema: 1.1.0
```

| Component | When to Bump | Example |
|-----------|--------------|---------|
| MAJOR | Breaking changes | Remove required field |
| MINOR | New optional fields | Add `git_sha` to receipt |
| PATCH | Bug fixes, clarifications | Fix enum typo |

Semver is appropriate for schemas because:
- They have strict compatibility requirements
- Readers need to know if they can parse
- Breaking changes must be explicit

## Flows: Date-Based (YYYY-MM-DD)

```yaml
flow_version: 2024-01-15
flow_key: build
```

Date-based because:
- Flows evolve incrementally
- No strict "compatibility" between versions
- Date provides context for when behavior changed
- Easier to track which version was active at a point in time

## Agents: Git SHA

Agent prompts live in the repository. Version is the commit SHA.

```yaml
agent_key: code-implementer
prompt_sha: a1b2c3d4
```

Why Git SHA:
- Prompts change frequently
- Exact version is traceable in history
- No manual version management required
- Can diff between any two versions easily

## Configs: Semantic Versioning

```yaml
config_version: 1.0.0
```

Registry formats, YAML structures, and tooling configs use semver because:
- They are consumed by deterministic tooling
- Breaking changes affect validation and parsing
- Clear compatibility signals are needed

## Version Registry

Current versions are tracked in a central location:

```yaml
# swarm/config/versions.yaml
schemas:
  receipt: 1.2.0
  handoff: 2.0.0
  envelope: 1.1.0
flows:
  signal: 2024-01-15
  plan: 2024-01-15
  build: 2024-01-15
  review: 2024-01-10
  gate: 2024-01-10
  deploy: 2024-01-08
  wisdom: 2024-01-08
config:
  agents: 1.0.0
  flows: 1.0.0
  profiles: 1.0.0
```

## The Rule

> Use the right versioning scheme for each artifact type.
> Schemas and configs use semver (compatibility matters).
> Flows use dates (evolution over compatibility).
> Agents use git SHA (automatic, traceable).

---

## See Also
- [versioning-compatibility.md](./versioning-compatibility.md) - What breaks vs what's safe
- [versioning-migration.md](./versioning-migration.md) - Reading old artifacts, migration scripts
- [receipt-schema.md](../artifacts/receipt-schema.md) - Current receipt format
