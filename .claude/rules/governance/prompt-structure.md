# Prompt Structure

**"Prompts are contracts, not suggestions."**

This rule defines the structure of effective agent prompts. For what to include and what to avoid, see the companion rules.

## Teaching Notes Format

Every agent prompt follows the teaching notes format. For the full specification, see [teaching-notes-contract.md](../artifacts/teaching-notes-contract.md).

### Required Sections

| Section | Purpose | Omission Risk |
|---------|---------|---------------|
| **Objective** | Single sentence: what this step accomplishes | Agent wanders |
| **Inputs** | Explicit paths to consumed artifacts | Agent invents data |
| **Outputs** | Explicit paths to produced artifacts | Artifacts get lost |
| **Behavior** | Role-specific instructions | Role confusion |
| **Success Criteria** | Measurable completion conditions | Agent claims "done" prematurely |
| **When Stuck** | Escape hatches for edge cases | Agent blocks unnecessarily |

### Minimal Valid Teaching Note

```markdown
## Objective
Implement the authentication module per ADR-005.

## Inputs
- `RUN_BASE/plan/adr.md` - Architecture decisions
- `RUN_BASE/plan/work_plan.md` - Task breakdown

## Outputs
- `src/auth.py` - Authentication implementation
- `tests/test_auth.py` - Unit tests
- `RUN_BASE/build/impl_notes.md` - Assumptions and decisions

## Behavior
- Follow ADR-005 OAuth2 specification
- Write tests before implementation
- Document assumptions in impl_notes.md

## Success Criteria
- All work_plan.md items marked complete
- pytest tests/test_auth.py exits 0
- No new lint errors (ruff check src/auth.py exits 0)

## When Stuck
- Ambiguous requirement: Document assumption, proceed with UNVERIFIED
- Missing dependency: Set BLOCKED with specific package name
- Test failure: Document failure, request iteration
```

## Context Loading Order

Prompts are assembled from context with strict priority:

| Priority | Content | Drop Policy |
|----------|---------|-------------|
| **CRITICAL** | Teaching notes, step spec | Never drop |
| **HIGH** | Previous step output | Truncate if over budget |
| **MEDIUM** | Referenced artifacts | Load on-demand |
| **LOW** | History summary, scent trail | Drop first |

### Budget Awareness

```markdown
## Context Budget
- Max input: 25000 tokens
- Priority order: teaching_notes > previous_step > artifacts > history
- If over budget: Drop history, then truncate artifacts
```

Agents do not decide what to load. The kernel loads based on priority. Prompts declare what matters.

## Validation Checklist

Before deploying a prompt, verify:

- [ ] Objective is one sentence, binary pass/fail
- [ ] All inputs have explicit paths
- [ ] All outputs have explicit paths
- [ ] Success criteria are measurable (exit codes, file existence, counts)
- [ ] Evidence requirements specify capture commands
- [ ] When Stuck covers: ambiguity, missing input, repeated failure
- [ ] No banned phrases (see [prompt-banned-patterns.md](./prompt-banned-patterns.md))
- [ ] No self-evaluation requests
- [ ] No open-ended questions
- [ ] Scope is bounded (explicit out-of-scope items)

## The Rule

> Every prompt has: objective, inputs, outputs, criteria, escape hatches.
> The kernel loads context by priority. Prompts declare what matters.

---

## See Also

- [teaching-notes-contract.md](../artifacts/teaching-notes-contract.md) - Full teaching notes specification
- [prompt-banned-patterns.md](./prompt-banned-patterns.md) - Patterns that produce unreliable behavior
- [prompt-required-patterns.md](./prompt-required-patterns.md) - Patterns that must be present
- [context-discipline.md](../execution/context-discipline.md) - Context loading rules
