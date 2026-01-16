# Prompt Banned Patterns

Vague prompts produce vague work.

## Banned Phrases

| Banned | Why | Use Instead |
|--------|-----|-------------|
| "Do your best" | Unmeasurable | "Ensure all tests pass" |
| "Be thorough" | Unmeasurable | "Check each requirement in spec.md" |
| "Fix everything" | Infinite scope | "Fix items 1-5 in work_plan.md" |
| "Try to" / "Maybe" | Implies optional | "Do X" or "If X then Y, else Z" |
| "Did you do a good job?" | Agents say yes | Run tests, check exit code |

## Banned Patterns

- **Self-evaluation**: Agents will claim success. Use independent critics.
- **Role mixing**: "Implement then review yourself" → one agent, one job
- **Narrative outputs**: "Explain what you did" → require artifact paths
- **Open-ended questions**: "What do you think?" → specific instructions

## The Rule

> Concrete beats vague. Binary beats hedged. Evidence beats narrative.
> If you cannot measure it, do not ask for it.
