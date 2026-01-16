# Prompt Structure

Prompts are contracts, not suggestions.

## Required Sections
| Section | Purpose |
|---------|---------|
| Objective | Single sentence, binary pass/fail |
| Inputs | Explicit paths to consumed artifacts |
| Outputs | Explicit paths to produced artifacts |
| Success Criteria | Measurable (exit codes, thresholds) |
| When Stuck | Situation → action → status table |

## Context Loading Priority
1. CRITICAL: Teaching notes (never drop)
2. HIGH: Previous step output (truncate if needed)
3. MEDIUM: Referenced artifacts (on-demand)
4. LOW: History/scent trail (drop first)

> Docs: docs/artifacts/TEACHING_NOTES.md
