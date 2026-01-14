# Prompt Required Patterns

**"Every prompt has: objective, inputs, outputs, criteria, escape hatches."**

These patterns must be present in every agent prompt. They enable measurable, verifiable work.

## Concrete Success Criteria

Success criteria must be measurable by the kernel, not judged by the agent.

**Good:**
```markdown
## Success Criteria
- `pytest tests/ -v` exits 0
- Coverage > 80% (evidence: coverage.json)
- No HIGH severity lint errors (evidence: ruff_output.log)
- All items in work_plan.md addressed
```

**Bad:**
```markdown
## Success Criteria
- Tests pass
- Good coverage
- Code is clean
```

**The difference:** Good criteria specify commands, thresholds, and evidence paths. Bad criteria are subjective and unmeasurable.

## Explicit Artifact Paths

Every input and output must have an explicit path. No vague references.

**Good:**
```markdown
## Outputs
- `src/auth/oauth.py` - OAuth2 implementation
- `tests/test_oauth.py` - OAuth2 tests
- `RUN_BASE/build/receipts/step-3-code.json` - Execution receipt
```

**Bad:**
```markdown
## Outputs
- Implementation code
- Tests
- Receipt
```

**The difference:** Good paths can be verified by `ls`. Bad paths require guessing.

## Evidence Requirements

Specify exactly what evidence to capture and how.

**Good:**
```markdown
## Evidence
Capture these for VERIFIED status:
- Test output: `pytest tests/ -v 2>&1 | tee RUN_BASE/build/test_output.log`
- Lint output: `ruff check src/ 2>&1 | tee RUN_BASE/build/lint_output.log`
- Diff summary: `git diff --stat > RUN_BASE/build/diff_summary.txt`
```

**Bad:**
```markdown
## Evidence
- Run tests
- Check linting
- Review changes
```

**The difference:** Good evidence specifies capture commands. Bad evidence is just task descriptions without output capture.

## Escape Hatches

Define what to do when things go wrong. Use a decision table.

**Good:**
```markdown
## When Stuck
| Situation | Action | Status |
|-----------|--------|--------|
| Ambiguous requirement | Document assumption in impl_notes.md | UNVERIFIED |
| Missing input file | Cite missing path | BLOCKED |
| Test failure after 3 attempts | Document failure, cite test output | UNVERIFIED |
| Dependency conflict | Document in concerns, proceed | UNVERIFIED |
```

**Bad:**
```markdown
## When Stuck
Ask for help.
```

**The difference:** Good escape hatches are specific, actionable, and assign status. Bad escape hatches create blocking conditions.

## Bounded Scope

Define both what is in scope and what is out of scope.

**Good:**
```markdown
## Scope
In scope:
- Implement OAuth2 login flow
- Add unit tests for new code
- Update API documentation

Out of scope:
- Refactoring existing auth code
- Performance optimization
- UI changes
```

**Bad:**
```markdown
## Behavior
Implement the authentication feature.
```

**The difference:** Explicit boundaries prevent scope creep. Unbounded work expands indefinitely.

## Structured Behavior Instructions

Use specific, verifiable instructions instead of general guidance.

**Good:**
```markdown
## Behavior
1. Read `RUN_BASE/plan/work_plan.md` for task list
2. For each task:
   - Implement the change
   - Write test covering the change
   - Verify test passes locally
3. Run `ruff check src/` and fix any errors
4. Write implementation notes to `RUN_BASE/build/impl_notes.md`
```

**Bad:**
```markdown
## Behavior
Implement the work plan items. Make sure to test your changes.
```

**The difference:** Good behavior is a procedure. Bad behavior is a wish.

## Evidence Binding

Claims must bind to evidence paths.

**Good:**
```markdown
## Handoff Requirements
For each claim, cite evidence:
- "Tests pass" requires: `test_output.log` path + exit code 0
- "Lint clean" requires: `lint_output.log` path + error count 0
- "Requirements met" requires: checklist with item-by-item status
```

**Bad:**
```markdown
## Handoff Requirements
Summarize what you did and confirm everything works.
```

**The difference:** Evidence binding prevents narrative substitution.

## The Rule

> Prompts are contracts, not suggestions.
> Every section serves a verification purpose.
> If the kernel cannot check it, do not claim it.

---

## See Also

- [prompt-structure.md](./prompt-structure.md) - Teaching notes format and validation
- [prompt-banned-patterns.md](./prompt-banned-patterns.md) - Patterns that produce unreliable behavior
- [evidence-discipline.md](./evidence-discipline.md) - What counts as evidence
- [teaching-notes-contract.md](../artifacts/teaching-notes-contract.md) - Full teaching notes specification
