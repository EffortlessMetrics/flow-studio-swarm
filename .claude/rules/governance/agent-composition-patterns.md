# Agent Composition Patterns

## Purpose

Define the four standard patterns for combining agents and the anti-patterns to avoid.

## The Rule

> Use composition patterns only when: work requires adversarial tension, expertise differs, or context would exceed budget. Every spawn must produce work or compression.

## 1. Sequential Chain

```
A ───► B ───► C
```

Each agent's output feeds the next.

**Use for:**
- Pipelines (raw -> structured -> validated)
- Transformations (spec -> code -> test)
- Progressive refinement

**Example:**
```
requirements-author -> requirements-critic -> adr-author
```

## 2. Adversarial Loop

```
┌─────────────────────────┐
│                         │
│   Author ────► Critic   │
│      ▲           │      │
│      └───────────┘      │
│                         │
└─────────────────────────┘
```

Iterate until exit condition met.

**Use for:**
- Quality improvement (code, tests, docs)
- Requirement refinement
- Review cycles

**Exit conditions:**
1. VERIFIED (no issues)
2. `can_further_iteration_help == false`
3. Iteration limit reached
4. Repeated failure signature

See [microloop-rules.md](../execution/microloop-rules.md) for details.

**Example:**
```
code-implementer <-> code-critic (max 5 iterations)
```

## 3. Fan-Out/Fan-In

```
             ┌──► A ──┐
             │        │
Coordinator ─┼──► B ──┼─► Aggregator
             │        │
             └──► C ──┘
```

Parallel work, then combine results.

**Use for:**
- Independent subtasks
- Parallel analysis
- Multi-file operations

**Example:**
```
impact-analyzer -> [file-analyzer-1, file-analyzer-2, ...] -> summary-aggregator
```

## 4. Specialist Delegation

```
Generalist ───► Specialist ───► Generalist
```

Deep dive on specific problem, then return.

**Use for:**
- Complex subproblems requiring expertise
- Security analysis mid-flow
- Performance investigation

**Example:**
```
code-implementer -> security-analyst -> code-implementer
```

## Anti-Patterns

| Anti-Pattern | Example | Problem |
|--------------|---------|---------|
| **Coordinator that routes** | `job: "Route work to agents"` | That's the orchestrator's job |
| **Validator that checks boolean** | `job: "Check if tests pass"` | That's a skill, no LLM needed |
| **Approver that rubber-stamps** | `job: "Approve if looks good"` | If it can't reject, don't spawn |
| **Agent per file** | `file-1-agent, file-2-agent...` | Over-decomposition, context loss |
| **Self-reviewing agent** | `job: "Write and review code"` | No adversarial tension |

## Spawning Cost

Each spawn costs:
- Fresh context window (~2k tokens overhead)
- Prompt overhead for role definition
- Handoff serialization/deserialization
- Potential context loss at boundaries

**The math:**
- 3 agents with 2k overhead each = 6k tokens wasted
- If task fits in one 30k context, don't shard

---

## See Also

- [agent-when-single-vs-multiple.md](./agent-when-single-vs-multiple.md) - When to use single vs multiple agents
- [agent-behavioral-contracts.md](./agent-behavioral-contracts.md) - Role families
- [microloop-rules.md](../execution/microloop-rules.md) - Adversarial loop exit conditions
- [scarcity-enforcement.md](./scarcity-enforcement.md) - Context budgets
