# Anti-Patterns

Every anti-pattern stems from:
1. Trusting narrative over physics
2. Lacking boundaries (scope, budget, exit criteria)
3. Mixing roles that should be separate
4. Doing manually what machines should do

## Agent Anti-Patterns

- **Self-evaluation**: Never ask agents if they succeeded. Run forensics.
- **Unbounded scope**: Every task needs measurable exit criteria.
- **Role mixing**: Writers never review own work. Critics never fix.
- **Narrative trust**: Claims without evidence are unverified.
- **Context drunk**: Curate context, don't load everything.

## Flow Anti-Patterns

- **Mid-flow blocking**: Complete flow, gate at boundary.
- **Scope creep**: If not in plan, not in build.
- **Skipping gates**: No merge without evidence panel check.
- **Premature optimization**: Make it work, then make it fast.

## Evidence Anti-Patterns

- **Hollow tests**: Execute without assert = not evidence.
- **Stale receipts**: Evidence must be from current commit.
- **Single metric**: Use panels. One number gets gamed.

## Economic Anti-Patterns

- **Premature abort**: Let runs complete. Partial runs are waste.
- **Runaway spending**: Set token and iteration budgets.
- **Manual grinding**: Machines generate, humans verify evidence.
