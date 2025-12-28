## Handoff Protocol

Every step ends with a handoff file that enables:
- Routing decisions (where to go next)
- Context transfer (what the next station needs to know)
- Audit trail (what was done and why)

### Status Meanings

- **VERIFIED**: Work complete, all requirements met, tests pass (if applicable)
- **UNVERIFIED**: Work attempted but issues remain (tests fail, incomplete)
- **PARTIAL**: Some progress made but blocked on something external
- **BLOCKED**: Cannot proceed due to missing inputs or invalid state

### can_further_iteration_help

- **yes**: Another iteration with the same station could fix remaining issues
- **no**: Issues require upstream changes or human intervention

This field controls microloop termination. Be honest - don't say "yes" forever.
