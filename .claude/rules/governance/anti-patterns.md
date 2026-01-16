# Anti-Patterns

Every anti-pattern stems from: trusting narrative over physics, lacking boundaries, mixing roles, or doing manually what machines should do.

## Agent

- **Self-evaluation**: Never ask agents if they succeeded. Run forensics.
- **Unbounded scope**: Every task needs measurable exit criteria.
- **Role mixing**: Writers never review own work. Critics never fix.
- **Context drunk**: Curate context, don't load everything.

## Flow

- **Mid-flow blocking**: Complete flow, gate at boundary. Don't halt for questions.
- **Scope creep**: If not in plan, not in build.
- **Skipping gates**: No merge without evidence panel check.

## Evidence

- **Hollow tests**: Execute without assert = not evidence
- **Stale receipts**: Evidence must be from current commit
- **Single metric**: Use panels. One number gets gamed.
- **Narrative substitution**: "Tests passed" without output = unverified

## Economic

- **Premature abort**: Let runs complete. Partial runs are waste.
- **Runaway spending**: Set token and iteration budgets.
- **Manual grinding**: Machines generate, humans verify evidence.

> Docs: docs/governance/ANTI_PATTERNS.md
