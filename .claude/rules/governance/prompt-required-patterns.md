# Prompt Required Patterns

Prompts are contracts, not suggestions.

## Every Prompt Must Have

1. **Objective**: One sentence, binary pass/fail
2. **Inputs**: Explicit paths to consumed artifacts
3. **Outputs**: Explicit paths to produced artifacts
4. **Success Criteria**: Measurable (exit codes, thresholds, evidence paths)
5. **When Stuck**: Decision table with situation → action → status

## The Rule

> If the kernel cannot check it, do not claim it.
> Criteria specify commands and evidence paths, not vibes.

## Bad → Good

- "Tests pass" → `pytest tests/ -v` exits 0
- "Implementation code" → `src/auth/oauth.py`
- "Ask for help" → Table mapping situations to actions and status values

> Docs: docs/CONTEXT_BUDGETS.md
