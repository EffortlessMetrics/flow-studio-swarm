# Teaching Notes Contract

Teaching notes are the contract between kernel and agent.

## Required Sections
| Section | Purpose |
|---------|---------|
| **Objective** | One sentence: what this step accomplishes |
| **Inputs** | Explicit paths to consumed artifacts |
| **Outputs** | Explicit paths to produced artifacts |
| **Behavior** | Role-specific instructions |
| **Success Criteria** | Measurable completion conditions |
| **When Stuck** | Escape hatches for edge cases |

## Optional Sections
- **Context Budget**: Token budget, priority order
- **Iteration Hints**: For microloop steps
- **Evidence Requirements**: What evidence to capture

## Loading Order

Flow-level defaults → step-specific overrides → runtime context (run_id, previous outputs).

## The Rule
- Required sections ensure agents know what to do
- "When Stuck" ensures graceful degradation
- Objective is one sentence, binary pass/fail
- Criteria specify commands and evidence paths

> Docs: docs/artifacts/TEACHING_NOTES.md
