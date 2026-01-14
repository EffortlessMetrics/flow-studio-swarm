# Agent Selection: Single vs Multiple

## Purpose

Decide when to use one agent vs many. The two reasons rule and composition test guide this decision.

## The Rule

> Spawn an agent for exactly two reasons: **Work** (something needs changing) or **Compression** (context needs compressing). If neither applies, don't spawn.

## The Two Reasons Rule

| Reason | Description | Example |
|--------|-------------|---------|
| **Work** | Something needs changing (code, docs, tests) | `code-implementer`, `test-author` |
| **Compression** | Context needs compressing (read lots, produce summary) | `impact-analyzer`, `context-loader` |

See [agent-behavioral-contracts.md](./agent-behavioral-contracts.md) for the full rule.

## Single Agent When

Use one agent when:

| Condition | Why |
|-----------|-----|
| Task is focused and bounded | Single responsibility = narrow trust |
| No conflicting roles | Writer shouldn't critique; critic shouldn't fix |
| Context fits in budget | No need to shard work |
| Clear success criteria | One agent can determine done |

### Examples

| Task | Agent | Why Single |
|------|-------|------------|
| Fix lint errors | `lint-fixer` | Narrow scope, clear exit |
| Write migration | `code-implementer` | Bounded by spec |
| Summarize codebase | `impact-analyzer` | Compression task |

## Multiple Agents When

Use multiple agents when:

| Condition | Why | Pattern |
|-----------|-----|---------|
| Adversarial tension needed | Writer shouldn't judge own work | Author + Critic |
| Different expertise required | Security != implementation | Specialist Delegation |
| Context would exceed budget | Shard to avoid pollution | Fan-Out/Fan-In |
| Parallel work possible | Independent subtasks | Fan-Out/Fan-In |

### Examples

| Task | Agents | Why Multiple |
|------|--------|--------------|
| Implement feature | `code-implementer` + `code-critic` | Adversarial quality |
| Full security review | `code-author` + `security-analyst` + `test-author` | Different expertise |
| Analyze large codebase | Multiple `context-loader` instances | Context sharding |

## The Composition Test

Before spawning additional agents, ask:

| Question | If Yes | If No |
|----------|--------|-------|
| Is there work product at the end? | Valid spawn | Don't spawn |
| Am I compressing information? | Valid spawn | Don't spawn |
| Is there adversarial tension needed? | Multiple agents | Single agent |
| Would single agent exceed context? | Shard work | Keep single |

All answers "no"? Don't spawn.

## Trust Implications

Composition affects trust:

| Pattern | Trust Level | Why |
|---------|-------------|-----|
| Single narrow agent | HIGH | Bounded scope, clear evidence |
| Adversarial loop | HIGH | Independent verification |
| Sequential chain | MEDIUM | Depends on weakest link |
| Fan-out/fan-in | MEDIUM | Aggregation quality matters |
| Broad coordinator | LOW | Scope too wide |

---

## See Also

- [agent-composition-patterns.md](./agent-composition-patterns.md) - The 4 composition patterns
- [agent-behavioral-contracts.md](./agent-behavioral-contracts.md) - Role families and the two reasons rule
- [narrow-trust.md](./narrow-trust.md) - Trust equation
- [scarcity-enforcement.md](./scarcity-enforcement.md) - Context budgets
