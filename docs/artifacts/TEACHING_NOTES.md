# Teaching Notes

Teaching notes are step-level contracts between kernel and agent.

## Required Sections

| Section | Purpose |
|---------|---------|
| Objective | One sentence, binary pass/fail |
| Inputs | Explicit paths to consumed artifacts |
| Outputs | Explicit paths to produced artifacts |
| Behavior | Role-specific instructions |
| Success Criteria | Measurable (commands + evidence paths) |
| When Stuck | Situation → action → status table |

## Loading Order

1. Flow-level defaults
2. Step-specific overrides
3. Runtime context (run_id, previous outputs)

## Rules

- No vibes; if the kernel can't check it, don't claim it
- Criteria specify commands and evidence paths
- "When Stuck" ensures graceful degradation
