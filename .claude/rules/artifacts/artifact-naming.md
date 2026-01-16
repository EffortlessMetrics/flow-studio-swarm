# Artifact Naming

Names should be predictable. Given flow, step, and agent, you should know the path.

## Conventions
- Lowercase with hyphens: `work-plan.md`, not `WorkPlan.md`
- Include step ID: `step-3-code-implementer.json`
- Include agent key for agent outputs: `<step>-<agent>.<ext>`

## Canonical Structure
```
RUN_BASE/<flow>/
├── receipts/<step>-<agent>.json
├── handoffs/<step>-<agent>.json
├── logs/<step>.jsonl
├── llm/<step>-<agent>-<engine>.jsonl
└── routing/decisions.jsonl
```

## What NOT to Include
- Timestamps in filenames
- Random IDs
- Spaces or special characters
- Version numbers (git handles versions)

## The Rule
- Paths are deterministic from (flow, step, agent)
- No lookup required—name tells you what it is
- Use forward slashes even on Windows
- No trailing slashes on directories

> Docs: docs/artifacts/NAMING_CONVENTIONS.md
