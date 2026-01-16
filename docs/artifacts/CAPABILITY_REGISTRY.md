# Capability Registry

Flows reference only registered capabilities/agents.

## Rules

- Add new agent keys to the registry before use
- No orphaned references (flows ↔ agents must be bijective)
- Renames/removals follow deprecation lifecycle

Pack-check enforces integrity; violations are errors.

See also: [AGENT_OPS.md](../AGENT_OPS.md)
