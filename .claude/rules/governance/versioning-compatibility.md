# Versioning Compatibility

Breaking changes require a migration path and staged rollout.

## The Rule
Breaking = changes that affect:
- Public contracts (schemas, CLI, APIs)
- Stored data formats
- External consumers / integrations

If breaking:
- Stage via deprecation lifecycle
- Provide migration guide before shipping the break
- Maintain compatibility window (old + new) when external dependents exist

> Skill: deprecation-migration
> Docs: docs/governance/VERSIONING.md
