# Economic Anti-Patterns

Mistakes in resource allocation, review efficiency, and compute economics.

## Premature Abort

**Pattern:** Killing runs that might succeed.

```
Human: "This is taking too long, cancel it."
*run was 80% complete with good forensics*
```

**Why it's wrong:** Compute is cheap. Partial runs are waste. A completed run with documented concerns is reviewable. A killed run is nothing.

**What to do instead:** Let runs complete. Review at gates.
```
Run status: Iteration 4 of 5
Forensics: Tests passing, lint clean
Action: Wait for completion, review evidence
```

**The rule:** An imperfect complete run is worth more than a perfect incomplete one.

---

## Runaway Spending

**Pattern:** No budget limits.

```
Agent: *iterates 50 times on diminishing returns*
Cost: $200 for a $20 task
```

**Why it's wrong:** Without limits, agents will iterate forever. They don't have judgment about cost-benefit. Iteration limits are guardrails.

**What to do instead:** Set token and iteration budgets.
```yaml
microloop:
  max_iterations: 3
  token_budget: 50000
  exit_on: VERIFIED or limit_reached
```

**The rule:** Scarcity is a feature. Budgets enforce discipline.

---

## Manual Grinding

**Pattern:** Doing what machines should do.

```
Human: *reads 5000 lines of code line by line*
Human: *manually runs each test to check*
```

**Why it's wrong:** This is the old model. Machines generate; humans verify evidence. Reading every line is grinding that should be automated.

**What to do instead:** Let the system grind. You audit.
```
System: Generates code, runs tests, captures evidence
Human: Reviews evidence panel, spot-checks hotspots
Time: 30 minutes vs 3 days
```

**The rule:** The machine does the implementation. You do the judgment.

---

## Review Theater

**Pattern:** Reading code instead of auditing evidence.

```
Reviewer: *reads 2000 lines of code carefully*
Reviewer: "Looks good to me"
*misses that tests weren't run*
```

**Why it's wrong:** Line-by-line review doesn't scale. It also doesn't catch what evidence catches—tests not run, coverage gaps, security issues. "Looks good" is vibes, not verification.

**What to do instead:** Audit evidence, spot-check hotspots.
```
1. Evidence exists? Fresh?
2. Panel metrics agree?
3. Spot-check 3-5 hotspots

This catches more than reading every line.
```

**The rule:** Review is evidence audit + hotspot sampling. Not line-by-line reading.

---

## See Also
- [anti-patterns-index.md](./anti-patterns-index.md) - Full quick reference
- [budget-discipline.md](./budget-discipline.md) - The $30 run
- [reviewer-protocol.md](./reviewer-protocol.md) - How to review efficiently
- [scarcity-enforcement.md](./scarcity-enforcement.md) - Budgets as design
