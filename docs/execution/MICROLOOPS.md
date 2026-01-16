# Microloops

Microloops are adversarial iteration: author ↔ critic.

## Exit Conditions (any)

1. VERIFIED: Critic finds no issues
2. No viable fix path: `can_further_iteration_help: false`
3. Iteration limit reached: Default 3 (Build code: 5)
4. Repeated failure signature: Same error twice → route to detour

## Critic Obligations

- Include `can_further_iteration_help: boolean`
- Cite concerns with file:line
- Rate severity
- **Never fix, only report**

## Author Obligations

- Address critic's concerns in priority order
- Produce measurable evidence of fix
- Don't over-fix (scope creep)

See also: [../explanation/ADVERSARIAL_LOOPS.md](../explanation/ADVERSARIAL_LOOPS.md)
