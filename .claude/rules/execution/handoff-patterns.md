# Handoff Patterns

Effective patterns for passing context between steps. Right-size handoffs prevent confusion and waste.

## The Problem

| Failure Mode | Symptom | Cost |
|--------------|---------|------|
| Too much context | Confusion, diluted focus | Token waste, wrong priorities |
| Too little context | Re-discovery, inconsistency | Repeated work, contradictions |
| Wrong context | Irrelevant work, drift | Wasted cycles, scope creep |

## Handoff Sizing

| Handoff Type | Target Size | Use Case |
|--------------|-------------|----------|
| **Minimal** | <500 tokens | Microloop iterations (critic <-> author) |
| **Standard** | 500-2000 tokens | Sequential steps (step N -> step N+1) |
| **Heavy** | 2000-5000 tokens | Cross-flow handoffs (Flow 2 -> Flow 3) |

### When to Use Each

**Minimal** - Fast iteration loops
- Critic -> author in microloop
- Single concern to address
- Status + issue + recommendation only

**Standard** - Normal step progression
- Between consecutive steps in same flow
- Includes summary, decisions, evidence pointers
- Most common handoff type

**Heavy** - Flow boundaries
- Flow 2 (Plan) -> Flow 3 (Build)
- Flow 5 (Gate) -> Flow 6 (Deploy)
- Includes full analysis, detailed findings, comprehensive context

## What to Include

Every handoff MUST include:

| Element | Purpose | Example |
|---------|---------|---------|
| **What I did** | Actions taken | "Implemented REQ-001 through REQ-005" |
| **What I found** | Key findings | "3 edge cases not covered in spec" |
| **What I decided** | Choices made (and why) | "Used OAuth over API keys per user request" |
| **Evidence pointers** | Paths to artifacts | `["RUN_BASE/build/test_output.log"]` |
| **What's next** | Recommendation | "Ready for critic review" |

## What to Exclude

Never include in handoffs:

| Excluded | Why |
|----------|-----|
| Full reasoning chains | Bloats context, pollutes focus |
| Abandoned approaches | Irrelevant to next step |
| Verbose explanations | Summarize instead |
| Raw tool outputs | Point to files, don't inline |
| Previous step's context | That's the scent trail's job |

## Compression Patterns

### Summarize, Don't Transcribe

```
# Bad: Transcribing
I ran pytest and it showed 47 tests passing including test_auth_login,
test_auth_logout, test_auth_refresh... [200 more lines]

# Good: Summarizing
Tests: 47 passed, 0 failed (evidence: RUN_BASE/build/test_output.log)
```

### Decisions Over Deliberation

```
# Bad: Deliberation
I considered using API keys but they have security issues, then I thought
about magic links but they require email infrastructure, so after weighing
the options I concluded that...

# Good: Decision
Decision: OAuth (alternatives rejected: API keys, magic links)
Rationale: User requested "standard login flow"
```

### Pointers Over Content

```
# Bad: Inlining content
Here's the full ADR I created:
# ADR-005: Authentication Strategy
## Context
[500 lines of ADR content]

# Good: Pointer
ADR created: RUN_BASE/plan/adr-005.md
Key decision: Use OAuth with PKCE flow
```

### Structured Over Prose

```
# Bad: Prose
The implementation is mostly complete. I wrote the auth module and
added some tests. There were a few issues I noticed...

# Good: Structured
Status: UNVERIFIED
Completed:
  - src/auth.py (OAuth handler)
  - tests/test_auth.py (12 test cases)
Concerns:
  - HIGH: Missing rate limiting (src/auth.py:42)
Evidence: RUN_BASE/build/impl_notes.md
```

## Context Loading on Receive

When a step receives a handoff:

### Always Load
- Teaching notes (step instructions)
- Handoff envelope (previous step's output)
- Scent trail (accumulated decisions)

### Conditionally Load
- Referenced artifacts (if teaching notes require them)
- Specific evidence files (if validation needed)

### Never Load
- Full conversation history
- Previous step's internal reasoning
- Unrelated artifacts
- Stale context from earlier runs

## Scent Trail vs Handoff

The scent trail is NOT a handoff. It's the accumulated decision history across all steps.

| Aspect | Handoff | Scent Trail |
|--------|---------|-------------|
| Scope | Single step output | All prior decisions |
| Updates | Replaced each step | Appended each step |
| Purpose | "What just happened" | "How we got here" |
| Size | Variable (500-5000) | Compact (~500-1000) |

### Scent Trail Prevents Re-litigation

Without scent trail:
```
Step 5: "Should we use OAuth or API keys?"
Step 6: "Should we use OAuth or API keys?"
Step 7: "Should we use OAuth or API keys?"
```

With scent trail:
```
Step 5: "Per scent trail, using OAuth (decided step 2). Implementing callback..."
Step 6: "Per scent trail, OAuth decided. Adding token refresh..."
Step 7: "Per scent trail, OAuth decided. Testing integration..."
```

## The Rule

> Right-size handoffs to their purpose.
> Minimal for loops. Standard for steps. Heavy for flow boundaries.
> Summarize, point, structure. Never transcribe.

## Anti-Patterns

### Context Hoarding
Loading everything "just in case."

**Problem:** Dilutes focus, wastes tokens, causes confusion.

**Fix:** Load only what teaching notes require.

### Context Starvation
Passing bare minimum to "save tokens."

**Problem:** Forces re-discovery, causes inconsistency.

**Fix:** Include decisions, evidence pointers, and assumptions.

### Inline Evidence
Pasting full tool outputs into handoffs.

**Problem:** Bloats context, obscures key information.

**Fix:** Write to file, include pointer.

### Narrative Handoffs
Writing prose instead of structured data.

**Problem:** Hard to parse, wastes tokens, hides information.

**Fix:** Use structured format with clear fields.

### Re-explaining Decisions
Restating prior decisions in each handoff.

**Problem:** Redundant, wastes tokens.

**Fix:** Scent trail carries decisions. Reference, don't restate.

---

## See Also
- [handoff-minimal.md](./handoff-minimal.md) - Minimal handoff examples for microloops
- [handoff-standard-heavy.md](./handoff-standard-heavy.md) - Standard and heavy handoff examples
- [context-discipline.md](./context-discipline.md) - Session amnesia and loading rules
- [handoff-protocol.md](../artifacts/handoff-protocol.md) - Envelope schema
- [scent-trail.md](../artifacts/scent-trail.md) - Decision provenance
