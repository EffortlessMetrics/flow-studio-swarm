# Anti-Patterns Index

Common mistakes that undermine the system. This index points to domain-specific anti-pattern catalogs.

## Quick Reference

| Category | Anti-Pattern | Fix |
|----------|-------------|-----|
| Agent | Self-evaluation | Measure with forensics |
| Agent | Unbounded scope | Define exit criteria |
| Agent | Role mixing | Separate author/critic |
| Agent | Narrative trust | Require evidence pointers |
| Agent | Context drunk | Curate context budget |
| Flow | Mid-flow blocking | Complete flow, gate at boundary |
| Flow | Scope creep | Stick to work plan |
| Flow | Skipping gates | Follow reviewer protocol |
| Flow | Premature optimization | Make it work first |
| Evidence | Hollow tests | Require assertions |
| Evidence | Stale receipts | Bind to commit SHA |
| Evidence | Single metric | Use panels |
| Evidence | Narrative substitution | Capture tool output |
| Economic | Premature abort | Let runs complete |
| Economic | Runaway spending | Set budgets |
| Economic | Manual grinding | Let machines grind |
| Economic | Review theater | Audit evidence |

## Domain Catalogs

| Catalog | Focus |
|---------|-------|
| [anti-patterns-agent.md](./anti-patterns-agent.md) | Self-evaluation, unbounded scope, role mixing, narrative trust, context drunk |
| [anti-patterns-flow.md](./anti-patterns-flow.md) | Mid-flow blocking, scope creep, skipping gates, premature optimization |
| [anti-patterns-evidence.md](./anti-patterns-evidence.md) | Hollow tests, stale receipts, single metric, narrative substitution |
| [anti-patterns-economic.md](./anti-patterns-economic.md) | Premature abort, runaway spending, manual grinding, review theater |

## The Meta-Rule

> Every anti-pattern stems from one of these errors:
> 1. Trusting narrative over physics
> 2. Lacking boundaries (scope, budget, exit criteria)
> 3. Mixing roles that should be separate
> 4. Doing manually what machines should do

When in doubt, ask:
- Is this claim backed by evidence?
- Is there a clear exit condition?
- Are the right roles doing the right jobs?
- Should a machine be doing this instead?

---

## See Also
- [evidence-discipline.md](./evidence-discipline.md) - What counts as evidence
- [factory-model.md](./factory-model.md) - The mental model that prevents these errors
- [narrow-trust.md](./narrow-trust.md) - Trust as a function of scope and evidence
- [panel-thinking.md](./panel-thinking.md) - Anti-Goodhart multi-metric verification
- [reviewer-protocol.md](./reviewer-protocol.md) - How to review without reading every line
