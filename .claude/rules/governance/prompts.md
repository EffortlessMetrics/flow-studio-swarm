# Prompts

Prompts are contracts, not suggestions.

## Required Sections

- **Objective**: Single sentence, binary pass/fail
- **Inputs**: Explicit paths to consumed artifacts
- **Outputs**: Explicit paths to produced artifacts
- **Success Criteria**: Measurable (exit codes, thresholds)
- **When Stuck**: Situation → action → status table

## Banned

- Vague: "Do your best", "Be thorough", "Fix everything"
- Hedged: "Try to", "Maybe"
- Self-evaluation: "Did you do a good job?"
- Role mixing: "Implement then review yourself"
- Narrative outputs: "Explain what you did"

## The Rule

- Concrete beats vague. Binary beats hedged. Evidence beats narrative.
- If the kernel cannot check it, do not claim it.
- If you cannot measure it, do not ask for it.

> Docs: docs/CONTEXT_BUDGETS.md
