# Prompt Banned Patterns

**"Vague prompts produce vague work."**

These patterns produce unreliable agent behavior. They are banned from prompts.

## Vague Instructions

Unmeasurable instructions give agents no target to hit.

| Banned | Why | Alternative |
|--------|-----|-------------|
| "Do your best" | Unmeasurable | "Ensure all tests pass" |
| "Be thorough" | Unmeasurable | "Check each requirement in spec.md" |
| "Consider carefully" | No output | "Document decision in ADR format" |
| "Make sure it works" | No criteria | "Exit code 0 on `pytest tests/`" |

## Unbounded Scope

Infinite scope leads to infinite work.

| Banned | Why | Alternative |
|--------|-----|-------------|
| "Fix everything" | Infinite scope | "Fix items 1-5 in work_plan.md" |
| "Improve the code" | No definition | "Reduce cyclomatic complexity below 10" |
| "Clean up" | No boundary | "Remove unused imports per ruff output" |
| "Make it production-ready" | Undefined | "Add error handling per contracts.md" |

## Self-Evaluation Requests

Agents are people-pleasers. They will claim success.

| Banned | Why | Alternative |
|--------|-----|-------------|
| "Did you do a good job?" | Agents say yes | Run tests, check exit code |
| "Are you confident?" | Agents say yes | Cite evidence or set UNVERIFIED |
| "Rate your work" | Self-serving | Critic agent evaluates |
| "Is this complete?" | Agents say yes | Check against success criteria |

## Hedging Language

Hedging implies the instruction is optional.

| Banned | Why | Alternative |
|--------|-----|-------------|
| "Try to" | Implies optional | "Do X" |
| "Maybe" | Implies optional | "If X then Y, else Z" |
| "If possible" | Ambiguous | "If X fails, set BLOCKED with reason" |
| "Consider" | No commitment | "Evaluate and document decision" |
| "Attempt to" | Implies failure OK | "Do X or set status to UNVERIFIED" |

## Anti-Pattern Examples

### Context Pollution

Loading irrelevant history wastes tokens and confuses the agent.

**Bad:**
```markdown
## Context
Load the entire conversation history so you understand what happened.
```

**Good:**
```markdown
## Context
Previous step produced: `RUN_BASE/plan/work_plan.md`
Scent trail: OAuth2 approach selected (ADR-005), using existing auth library
```

**Rule:** Load artifacts, not conversation. Scent trail provides decision history.

### Role Confusion

Mixing roles produces poor work in both domains.

**Bad:**
```markdown
## Behavior
Implement the code, then review it yourself to make sure it's correct.
Write tests and verify they're comprehensive enough.
```

**Good:**
```markdown
## Behavior (Implementer)
Implement the code per spec. Write tests. Set status to UNVERIFIED.
```

**Rule:** One agent, one job. Critics never fix. Implementers never self-review.

### Narrative Over Evidence

Asking for explanations instead of receipts produces prose, not proof.

**Bad:**
```markdown
## Outputs
- Explanation of what you implemented
- Summary of how you tested it
- Description of any issues you found
```

**Good:**
```markdown
## Outputs
- `src/auth.py` - Implementation (artifact)
- `RUN_BASE/build/test_output.log` - pytest output (evidence)
- `RUN_BASE/build/concerns.json` - Structured issues with file:line (evidence)
```

**Rule:** Evidence is files and exit codes. Narrative is not evidence.

### Open-Ended Questions

Questions invite rambling. Statements invite compliance.

**Bad:**
```markdown
## Behavior
What do you think is the best approach for implementing authentication?
How should we handle error cases?
```

**Good:**
```markdown
## Behavior
Implement authentication using OAuth2 per ADR-005.
Handle errors by returning structured error responses per contracts.md.
```

**Rule:** Prompts are instructions, not conversations.

### Missing Constraints

Unconstrained work expands to fill available context.

**Bad:**
```markdown
## Behavior
Refactor the authentication module to improve quality.
```

**Good:**
```markdown
## Behavior
Refactor `src/auth.py`:
- Extract `validate_token()` to `src/auth/validators.py`
- Add type hints to all public functions
- Do NOT modify `src/auth/legacy.py` (out of scope)
```

**Rule:** Define what is in scope AND what is out of scope.

## The Rule

> Concrete beats vague. Binary beats hedged. Evidence beats narrative.
> If you cannot measure it, do not ask for it.

---

## See Also

- [prompt-structure.md](./prompt-structure.md) - Teaching notes format and validation
- [prompt-required-patterns.md](./prompt-required-patterns.md) - Patterns that must be present
- [evidence-discipline.md](./evidence-discipline.md) - What counts as evidence
- [agent-behavioral-contracts.md](./agent-behavioral-contracts.md) - Role family rules
