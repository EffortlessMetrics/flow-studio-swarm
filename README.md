# Flow Studio

> A trust compiler for the industrialized SDLC.

**This is not a code generator. It's a verification infrastructure that happens to generate code.**

The system's job isn't to write code—it's to produce reviewable trust bundles that minimize the attention cost of verification. Code is a side effect. Evidence is the product.

**For:** Platform engineers, agent architects, and teams building agentic SDLC tooling at scale.

---

## The Core Thesis

**Code generation is cheap. Trust is expensive.**

Models write code at 1,000+ tokens/second. The bottleneck isn't "can it write code"—it's "can a human review and trust the output in 30 minutes instead of spending a week doing it themselves."

**The trade:** Spend $2.00 on compute that produces a reviewable PR with evidence. Don't spend 5 days of developer time producing something worse.

**What this system produces:**
- **Receipts** — Proof of what happened, with forensic evidence
- **Evidence panels** — Multi-metric verification that resists gaming
- **Bounded artifacts** — Changes with clear scope and audit trail
- **Trust bundles** — The actual product; code is a side effect

> The verification stack is the crown jewel, not the codebase.

The system does the repetitions. Humans do the decisions.

---

## The Factory Mental Model

Do not anthropomorphize AI agents as "copilots" or "partners." View the system as a manufacturing plant.

| Component | Role | Behavior |
|-----------|------|----------|
| **Python Kernel** | Factory Foreman | Deterministic, strict. Manages time, disk, budget. Never guesses; enforces. |
| **Agents** | Enthusiastic Interns | Brilliant and tireless. Prone to "hallucinating success" to please. Need boundaries. |
| **Disk** | Ledger | If it isn't written to `RUN_BASE/`, it didn't happen. |
| **Receipts** | Audit Trail | The product. Not the code. |

**The foreman's job:** Don't ask interns if they succeeded—measure the bolt. Don't give them everything—curate what they need. Don't trust their prose—trust their receipts.

---

## What Flow Studio Is (and Isn't)

**Flow Studio IS:**
- A **trust compiler** that transforms intent into auditable evidence
- A **flow orchestrator** that executes structured SDLC steps with durable state
- A **PR cockpit generator** that produces reviewable evidence packages

**Flow Studio is NOT:**
- A code generator (it orchestrates agents that generate; it doesn't generate itself)
- A chatbot (there's no conversation—assign tickets, audit outputs)
- A CI replacement (it produces artifacts that CI consumes and validates)

---

## What Makes This Different

| Principle | What it means |
|-----------|---------------|
| **Forensics over narrative** | We ignore prose explanations. Trust the git diff, the test log, the receipt. If it's not on disk, it didn't happen. |
| **Verification is the product** | The output isn't code—it's code plus the evidence needed to trust it. |
| **Steps, not sessions** | Each step has one job in a fresh context. No "context drunkenness" from 100k-token sessions. |
| **PARTIAL is a save point** | Agents exit honestly when blocked. Resume later with zero data loss. |

---

## The Seven Flows

| Flow | What happens | What you get |
|------|--------------|--------------|
| **Signal** | Shape vague input into rigid acceptance criteria | requirements, BDD scenarios, risks |
| **Plan** | Design before writing logic | ADR, contracts, work plan |
| **Build** | Implement with adversarial loops | code, tests, build receipt |
| **Review** | Harvest feedback, apply fixes | drained worklist, ready PR |
| **Gate** | Forensic audit of the diff | MERGE or BOUNCE verdict |
| **Deploy** | Merge to mainline | CI verification, audit trail |
| **Wisdom** | Extract learnings | feedback actions, pattern library |

---

## Quick Start

```bash
uv sync --extra dev
make demo-run          # Populate example run
make flow-studio       # Start UI at http://localhost:5000
```

Open: `http://localhost:5000/?run=demo-health-check&mode=operator`

**What you'll see:**
- Left sidebar: 7 flows
- Center: Step graph for selected flow
- Top bar: SDLC progress (all green for the demo)
- Right panel: Agent details and artifacts

---

## Essential Commands

```bash
make dev-check         # Validate swarm health (run before commits)
make selftest          # Full 16-step validation
make kernel-smoke      # Fast kernel check (~300ms)
make stepwise-sdlc-stub # Run stepwise demo (zero-cost stub)
make help              # Show all commands
```

---

## Architecture

Three planes, cleanly separated:

| Plane | Component | What it does |
|-------|-----------|--------------|
| **Control** | Python kernel | Manages state, budgets, atomic disk commits |
| **Execution** | Claude Agent SDK | Autonomous agent work in a sandbox |
| **Projection** | DuckDB | Fast queryable index for the UI |

The kernel is deterministic. The agent is autonomous. The database is ephemeral (rebuildable from `events.jsonl`).

> **Flow Studio is implemented in Python (kernel/runtime) and TypeScript (UI).** It orchestrates work in repos of any language.

**Step lifecycle:**
1. **Work** — Agent executes with full autonomy
2. **Finalize** — JIT prompt forces structured `handoff_envelope.json`
3. **Route** — Separate call proposes next state transition

Kill the process at any point. Resume with zero data loss.

---

## Documentation

### Start Here

| Time | Document | What you'll learn |
|------|----------|-------------------|
| 10 min | [GETTING_STARTED.md](docs/GETTING_STARTED.md) | Run the demo, see it work |
| 20 min | [TOUR_20_MIN.md](docs/TOUR_20_MIN.md) | Understand the full system |
| 5 min | [MARKET_SNAPSHOT.md](docs/MARKET_SNAPSHOT.md) | Why this approach, why now |

### Go Deeper

| Topic | Document |
|-------|----------|
| Flow Studio UI | [FLOW_STUDIO.md](docs/FLOW_STUDIO.md) |
| Stepwise execution | [STEPWISE_BACKENDS.md](docs/STEPWISE_BACKENDS.md) |
| Reviewing PRs | [REVIEWING_PRS.md](docs/REVIEWING_PRS.md) |
| Quality event types | [QUALITY_EVENTS.md](docs/QUALITY_EVENTS.md) |
| Adopt for your repo | [ADOPTION_PLAYBOOK.md](docs/ADOPTION_PLAYBOOK.md) |
| Example runs | [GOLDEN_RUNS.md](docs/GOLDEN_RUNS.md) |
| Full reference | [CLAUDE.md](CLAUDE.md) |
| All docs | [docs/INDEX.md](docs/INDEX.md) |

### Philosophy

| Topic | Document |
|-------|----------|
| AgOps manifesto | [AGOPS_MANIFESTO.md](docs/AGOPS_MANIFESTO.md) |
| What this system is | [TRUST_COMPILER.md](docs/explanation/TRUST_COMPILER.md) |
| 15 implementation lessons | [META_LEARNINGS.md](docs/explanation/META_LEARNINGS.md) |
| 12 emergent laws | [EMERGENT_PHYSICS.md](docs/explanation/EMERGENT_PHYSICS.md) |
| Why this design | [WHY_DEMO_SWARM.md](docs/WHY_DEMO_SWARM.md) |
| All explanation docs | [docs/explanation/](docs/explanation/README.md) |

---

## Operational Invariants

These aren't suggestions—they're load-bearing walls:

- **Shadow fork isolation** — Work happens in a fork to prevent "moving target" hallucinations
- **Atomic commits** — State moves only after the handoff envelope is durable
- **DB-backed UI** — TypeScript queries DuckDB, not JSONL parsing—instant at any scale
- **Agent-driven routing** — Next-step decisions come from agents who understand context, not regex

---

## The Three Questions

Every reviewer should be able to answer these in under 5 minutes:

1. **Does evidence exist and is it fresh?** — Receipts must exist and come from this commit
2. **Does the panel of metrics agree?** — Contradictions reveal problems
3. **What would I spot-check with 5 minutes?** — The hotspots list guides you to 3-8 files

If you can answer these, you can review the PR. The system did the grinding; you do the judgment.

---

## Ready to Adopt?

Before adopting, ensure you have:

- [ ] Run `make dev-check` and confirmed green
- [ ] Read [GETTING_STARTED.md](docs/GETTING_STARTED.md)
- [ ] Reviewed [GOLDEN_RUNS.md](docs/GOLDEN_RUNS.md) examples
- [ ] Understood [STEPWISE_BACKENDS.md](docs/STEPWISE_BACKENDS.md)

See [ADOPTION_PLAYBOOK.md](docs/ADOPTION_PLAYBOOK.md) for the complete checklist.

---

## Related

- [EffortlessMetrics/demo-swarm](https://github.com/EffortlessMetrics/demo-swarm) — Portable `.claude/` pack for your own repo

---

## Status

Early re-implementation of a proven pattern. Bundled examples work; outside those, you're exploring.

Something broken? [Open an issue](../../issues).

---

## License

Apache-2.0 or MIT
