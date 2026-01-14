# Agent Anti-Patterns

Mistakes in how agents are tasked, evaluated, and composed.

## Self-Evaluation

**Pattern:** Asking agents if they did well.

```
Orchestrator: "Did the implementation succeed?"
Agent: "Yes, I successfully implemented all requirements."
```

**Why it's wrong:** Agents are people-pleasers. They will claim success to avoid disappointing you. This is the intern psychology at work—they want to report good news.

**What to do instead:** Measure the bolt.
```
Receipt: exit_code=0, tests_passed=47, coverage=94%
```

**The rule:** Never ask interns if they succeeded. Run the forensics.

---

## Unbounded Scope

**Pattern:** "Fix all the things" with no exit criteria.

```
Task: "Improve the codebase quality"
Agent: *refactors for 50 iterations, never finishes*
```

**Why it's wrong:** Without boundaries, agents will iterate forever. They don't have judgment about when "enough is enough." Every task needs measurable exit criteria.

**What to do instead:** Define specific, measurable outcomes.
```
Task: "Reduce lint errors to zero in src/auth.py"
Exit: lint_errors == 0 for target file
```

**The rule:** Every task needs exit criteria that a machine can verify.

---

## Role Mixing

**Pattern:** Same agent writes and reviews.

```
Agent: "I wrote the code, and I reviewed it. Looks great!"
```

**Why it's wrong:** No adversarial tension. Self-review produces self-approval. The author is kind to their own work. This is why microloops exist—separate author from critic.

**What to do instead:** Author and critic are always different agents.
```
code-implementer → (writes) → code-critic → (reviews harshly)
```

**The rule:** Writers never review their own work. Critics never fix.

---

## Narrative Trust

**Pattern:** Believing prose over receipts.

```
Agent: "All tests pass and the implementation is complete."
Human: "Great, let's merge."
```

**Why it's wrong:** Narrative is the lowest tier in the truth hierarchy. "Tests pass" is a claim. `pytest exit_code=0` is physics. Trust physics.

**What to do instead:** Require evidence pointers.
```
Claim: "All tests pass"
Evidence required: test_output.log, exit_code=0
```

**The rule:** Claims without evidence are unverified. "Not measured" is valid. False certainty is not.

---

## Context Drunk

**Pattern:** Loading everything, focusing on nothing.

```
Context: 500 pages of documentation
Agent: *confused, misses the actual task*
```

**Why it's wrong:** Too much context causes confusion. Agents are brilliant but inexperienced—they can't prioritize within a sea of information. This is context drunkenness.

**What to do instead:** Curate what agents need.
```
Context Pack:
  - teaching_notes.md (CRITICAL - always loaded)
  - previous_output.md (HIGH - budgeted)
  - relevant artifacts only (MEDIUM - on-demand)
```

**The rule:** Don't give them everything. Curate what they need. Intelligence degrades as irrelevant history grows.

---

## See Also
- [anti-patterns-index.md](./anti-patterns-index.md) - Full quick reference
- [agent-behavioral-contracts.md](./agent-behavioral-contracts.md) - Role family definitions
- [factory-model.md](./factory-model.md) - The intern psychology
- [evidence-discipline.md](./evidence-discipline.md) - What counts as evidence
- [scarcity-enforcement.md](./scarcity-enforcement.md) - Context budgets
