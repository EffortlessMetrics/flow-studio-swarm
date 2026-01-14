# Flow Anti-Patterns

Mistakes in how flows are executed, gated, and optimized.

## Mid-Flow Blocking

**Pattern:** Stopping for human input in the middle of a flow.

```
Step 3: "I have a question. Should we use OAuth or API keys?"
*flow halts, waits for human*
```

**Why it's wrong:** Mid-flow escalation creates babysitting overhead. Humans must monitor runs, answer questions, unblock agents. Stalled flows are waste.

**What to do instead:** Complete the flow. Document the assumption. Gate at boundary.
```json
{
  "status": "UNVERIFIED",
  "assumptions": [{
    "assumption": "Using OAuth (most common pattern)",
    "impact_if_wrong": "Would need auth module refactor"
  }]
}
```

**The rule:** Flows complete; gates review. Humans answer questions at flow boundaries, not mid-flow.

---

## Scope Creep

**Pattern:** Adding features during build that weren't in plan.

```
Plan: "Implement user login"
Build: "While I'm here, I also added password reset, 2FA, and social login"
```

**Why it's wrong:** Every routing decision must pass the charter test: "Does this help achieve the flow's objective?" Unplanned features are scope creep—they bloat review, introduce risk, and violate the plan.

**What to do instead:** Stick to the work plan. Log out-of-scope ideas for future work.
```
Work plan items: REQ-001, REQ-002, REQ-003
Completed: REQ-001, REQ-002, REQ-003
Out of scope (deferred): Password reset idea noted in observations
```

**The rule:** If it's not in the plan, it's not in the build. Charters prevent drift.

---

## Skipping Gates

**Pattern:** "It looks fine" without evidence.

```
Reviewer: "The agent said it works, let's merge."
*merges without checking evidence panel*
```

**Why it's wrong:** This is narrative trust at the flow level. Gates exist to verify evidence, not rubber-stamp claims. "Looks fine" is not review.

**What to do instead:** Follow the reviewer protocol.
```
1. Does evidence exist and is it fresh? (30 sec)
2. Does the panel of metrics agree? (30 sec)
3. What would I spot-check with 5 minutes? (use hotspots)
```

**The rule:** No merge without evidence. The system did the grinding; you verify the receipts.

---

## Premature Optimization

**Pattern:** Optimizing flows before they work.

```
"Let's add caching to reduce token cost"
*flow doesn't even complete successfully yet*
```

**Why it's wrong:** Can't optimize what doesn't work. First make it work, then make it fast, then make it cheap. Premature optimization is yak shaving.

**What to do instead:** Get the flow working end-to-end first.
```
Phase 1: Flow completes successfully
Phase 2: Measure actual bottlenecks
Phase 3: Optimize based on evidence
```

**The rule:** Working beats fast. Evidence before optimization.

---

## See Also
- [anti-patterns-index.md](./anti-patterns-index.md) - Full quick reference
- [flow-charters.md](./flow-charters.md) - Flow objectives and non-goals
- [fix-forward-vocabulary.md](./fix-forward-vocabulary.md) - BLOCKED is rare
- [reviewer-protocol.md](./reviewer-protocol.md) - How to review properly
