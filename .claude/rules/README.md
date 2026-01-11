# AgOps Rules Registry

This directory contains the governance rules for Flow Studio's agentic operations.
These rules encode Steven Zimmerman's AI-native development philosophy: **trade compute for senior attention**.

## Rule Categories

| Directory | Purpose | Enforcement |
|-----------|---------|-------------|
| `governance/` | Agent behavioral contracts, state machines, error handling | Agent prompts + validation |
| `execution/` | Context budgets, routing decisions, microloop limits | Runtime kernel |
| `artifacts/` | Receipt schemas, handoff protocols, audit trails | `receipt_io.py` + validation |
| `safety/` | Git safety, branch protection, secrets, permissions | Hooks + boundary agents |

## Core Principle

**Rules are constitution; docs are textbook.**

- Rules define what MUST happen (enforced)
- Docs explain WHY it happens (teaching)
- Pack-check validates COMPETENCE, not schema compliance

## The Physics Stack

Rules encode the "physics" that make autonomous operation safe:

1. **Truth Hierarchy** - What counts as evidence (physics > receipts > narrative)
2. **Session Amnesia** - Each step starts fresh; disk is memory
3. **Mechanical Truth** - Never ask models to judge success; measure it
4. **Contained Blast Radius** - Work can be destructive inside the sandbox; publishing is gated
5. **Bounded Routing** - Kernel generates candidates; Navigator selects; kernel validates
6. **Narrow Trust** - Scope narrowness × evidence quality × verification depth
7. **Navigator Protocol** - Forensics-based routing with bounded decisions

---

## Physics Enforcement Hierarchy

When physics conflict, this is the resolution order. Higher principles override lower ones.

### 1. Truth Hierarchy (Highest Priority)

**Physics beats narrative. Always.**

When an agent claims "tests passed" but pytest exit code is non-zero, trust the exit code.
When a receipt says "clean" but git status shows uncommitted files, trust git.

| Level | Source | Trust |
|-------|--------|-------|
| Physics | Exit codes, file hashes, git status | Absolute |
| Receipts | Captured tool output, logs | High |
| Artifacts | Generated files, diffs | Medium |
| Narrative | Agent claims, prose | Lowest |

**Enforcement**: `receipt_io.py` validates evidence pointers; Gate agents require evidence before merge recommendation.

### 2. Boundary Physics

**Publish gates are real; internal gates are routing.**

Inside the shadow fork (Flows 1-5): full autonomy. Any git operation permitted.
At publish boundary (Flow 6): strict controls. Secrets scan, evidence verification, no force push.

This principle means:
- Internal "failures" are routing signals, not hard stops
- External publishing has hard stops (secrets, missing evidence)
- BLOCKED inside a flow is exceptional; BLOCKED at boundary is enforced

**Enforcement**: `boundary-automation.md` defines the gate; Flow 6 runs secrets scan before upstream push.

### 3. Evidence Discipline

**Existence + freshness required.**

Evidence must:
- Exist (file path resolves)
- Be fresh (from this commit, not stale)
- Be corroborated (multiple sources agree when possible)

"Not measured" is honest and valid. False certainty is not.

**Enforcement**: `receipt-schema.md` requires evidence paths; Gate agents verify freshness via commit SHA.

### 4. Narrow Trust

**Trust = Scope × Evidence × Verification**

A narrow agent with strong evidence is more trustworthy than a broad agent with weak evidence.

| Factor | High Value | Low Value |
|--------|------------|-----------|
| Scope | Single job, bounded blast radius | "Do everything" |
| Evidence | Physics-level proof | Narrative claims |
| Verification | Multiple independent checks | Self-reported |

**Enforcement**: Agent behavioral contracts define single jobs; role families constrain scope.

### 5. Session Amnesia (Lowest Priority)

**Disk is memory; chat is ephemeral.**

Each step starts fresh. Prior conversation is NOT a dependency. Continuity comes from:
- Artifacts on disk
- Handoff envelopes
- Scent trail (decision breadcrumbs)

This principle yields to the above when:
- Evidence requires loading prior artifacts (truth hierarchy wins)
- Context budgets constrain what can be loaded (scarcity enforcement)

**Enforcement**: `context-discipline.md` defines rehydration from artifacts, not conversation.

### Conflict Resolution Examples

| Conflict | Resolution |
|----------|------------|
| Agent says "done" but tests fail | Truth hierarchy: tests fail = not done |
| Internal step wants to block | Boundary physics: route forward, document concern |
| Evidence exists but is stale | Evidence discipline: re-run or flag as unverified |
| Broad agent claims success | Narrow trust: require more evidence for broad claims |
| Need prior context but budget exceeded | Session amnesia + scarcity: load only critical items |

---

## FR-XXX to Rules Mapping

Each FR validation rule implements or supports specific physics rules.

| FR Rule | Primary Purpose | Implementing Rules | Status |
|---------|-----------------|-------------------|--------|
| **FR-001** | Agent registry bijection | `agent-behavioral-contracts.md` (single job), `narrow-trust.md` (scope) | Enforced |
| **FR-002** | Frontmatter validity | `agent-behavioral-contracts.md` (role families), `model-policy.md` (model allocation) | Enforced |
| **FR-002b** | Color semantics | `agent-behavioral-contracts.md` (role family colors) | Enforced |
| **FR-003** | Flow reference validity | `flow-charters.md` (flow structure), `routing-decisions.md` (agent routing) | Enforced |
| **FR-004** | Skill file validity | `teaching-notes-contract.md` (skill instructions) | Enforced |
| **FR-005** | RUN_BASE path hygiene | `receipt-schema.md` (artifact placement), `handoff-protocol.md` (envelope paths) | Enforced |
| **FR-006** | Prompt section completeness | `teaching-notes-contract.md` (required sections), `agent-behavioral-contracts.md` (handoff) | Supported |
| **FR-006a** | Microloop phrase bans | `microloop-rules.md` (exit conditions), `fix-forward-vocabulary.md` (status semantics) | Enforced |
| **FR-007** | Capability evidence | `capability-registry.md` (evidence binding), `evidence-discipline.md` (claim verification) | Enforced |
| **FR-CONF** | Config coverage | `agent-behavioral-contracts.md` (role families), `model-policy.md` (model tiers) | Enforced |
| **FR-FLOWS** | Flow invariants | `flow-charters.md` (flow structure), `routing-decisions.md` (step connectivity) | Enforced |

### Physics Enforcement by FR Rule

| FR Rule | Primary Physics Enforced |
|---------|-------------------------|
| FR-001, FR-002, FR-002b | Narrow Trust (scope definition) |
| FR-003, FR-FLOWS | Bounded Routing (flow structure) |
| FR-005 | Session Amnesia (artifact placement) |
| FR-006, FR-006a | Mechanical Truth (exit conditions) |
| FR-007 | Truth Hierarchy (evidence over claims) |
| FR-CONF | Narrow Trust (role family constraints) |

---

## Implementation Status Convention

Rules indicate their enforcement status. This prevents claiming capabilities that aren't actually enforced.

### Status Definitions

| Status | Meaning | Indicator |
|--------|---------|-----------|
| **Enforced** | Automated validation exists and runs in CI | Cite: `validate_swarm.py` function or hook |
| **Supported** | Code exists but validation is incomplete or optional | Cite: code path + what's missing |
| **Designed** | Spec exists, implementation pending | Cite: design doc or rule file |

### Current Rule Status

#### Governance Rules

| Rule | Status | Enforcement Point |
|------|--------|-------------------|
| `agent-behavioral-contracts.md` | Enforced | `validate_bijection()`, `validate_frontmatter()`, `validate_colors()` |
| `evidence-discipline.md` | Supported | `receipt_io.py` validates structure; freshness check not automated |
| `fix-forward-vocabulary.md` | Designed | Semantic validation of BLOCKED usage not automated |
| `flow-charters.md` | Supported | Flow structure validated; goal-alignment not automated |
| `model-policy.md` | Enforced | `validate_frontmatter()` checks model values |
| `narrow-trust.md` | Supported | Scope via role families; trust calculation not automated |
| `pack-check-philosophy.md` | Enforced | This IS the validation philosophy |
| `panel-thinking.md` | Designed | Gate agents implement; no automated panel checks |
| `truth-hierarchy.md` | Supported | `receipt_io.py` structure; hierarchy not enforced |

#### Execution Rules

| Rule | Status | Enforcement Point |
|------|--------|-------------------|
| `context-discipline.md` | Supported | Kernel implements; no validation of context loading |
| `detour-catalog.md` | Designed | Detour patterns defined; matching not automated |
| `microloop-rules.md` | Enforced | `validate_microloop_phrases()` bans old patterns |
| `navigator-protocol.md` | Supported | Kernel routing exists; validation incomplete |
| `resume-protocol.md` | Designed | Checkpoint spec exists; resume logic partial |
| `routing-decisions.md` | Supported | Vocabulary defined; routing validation incomplete |
| `subsumption-principle.md` | Supported | Transport capabilities declared; subsumption partial |

#### Artifact Rules

| Rule | Status | Enforcement Point |
|------|--------|-------------------|
| `capability-registry.md` | Enforced | `validate_capability_registry()` |
| `handoff-protocol.md` | Supported | Schema defined; envelope validation partial |
| `receipt-schema.md` | Enforced | `receipt_io.py` validates required fields |
| `scent-trail.md` | Designed | Schema defined; trail generation not implemented |
| `teaching-notes-contract.md` | Supported | `validate_prompt_sections()` checks some sections |

#### Safety Rules

| Rule | Status | Enforcement Point |
|------|--------|-------------------|
| `git-safety.md` | Supported | Shadow fork model; boundary checks via Flow 6 |
| `sandbox-and-permissions.md` | Enforced | `.claude/settings.json` deny patterns |
| `boundary-automation.md` | Designed | Secrets scan spec; automation pending |

### Adding New Rules

When adding a new rule, include status frontmatter:

```yaml
---
status: designed | supported | enforced
enforcement: <citation or "pending">
---
```

This creates an audit trail from spec to enforcement

## Rule Registry

### Governance Rules
| Rule | Purpose |
|------|---------|
| `agent-behavioral-contracts.md` | PM/IC model, role families, status reporting |
| `evidence-discipline.md` | Sheriff pattern, what counts as evidence |
| `fix-forward-vocabulary.md` | Valid outcomes, BLOCKED is rare |
| `flow-charters.md` | Goals, exit criteria, non-goals per flow |
| `model-policy.md` | Model allocation by role family |
| `narrow-trust.md` | Trust equation: scope × evidence × verification |
| `pack-check-philosophy.md` | Competence over compliance validation |
| `panel-thinking.md` | Anti-Goodhart multi-metric panels |
| `truth-hierarchy.md` | Evidence levels (physics > receipts > narrative) |

### Execution Rules
| Rule | Purpose |
|------|---------|
| `context-discipline.md` | Session amnesia, rehydration pattern |
| `detour-catalog.md` | Known fix patterns (lint, import, type, etc.) |
| `microloop-rules.md` | Exit conditions, fuse detection |
| `navigator-protocol.md` | Routing brain: forensics → decision → validation |
| `resume-protocol.md` | Checkpoint semantics, crash recovery |
| `routing-decisions.md` | Decision vocabulary (CONTINUE, LOOP, DETOUR, etc.) |
| `subsumption-principle.md` | Kernel compensates for backend gaps |

### Artifact Rules
| Rule | Purpose |
|------|---------|
| `capability-registry.md` | Evidence binding for capability claims |
| `handoff-protocol.md` | Envelope structure for step transitions |
| `receipt-schema.md` | Required fields for audit trail |
| `scent-trail.md` | Decision provenance breadcrumbs |
| `teaching-notes-contract.md` | Required sections for step instructions |

### Safety Rules
| Rule | Purpose |
|------|---------|
| `git-safety.md` | Prohibited operations, conflict resolution |
| `sandbox-and-permissions.md` | Containment checklist, boundary model |

## Usage

Rules are automatically loaded by Claude Code from this directory.
Path-specific rules use frontmatter to scope application.

## Cross-References

Rules are the **enforcement layer**. Teaching docs explain the **why**.

| Rule | Teaching Doc |
|------|--------------|
| `truth-hierarchy.md` | [TRUTH_HIERARCHY.md](../../docs/explanation/TRUTH_HIERARCHY.md) |
| `narrow-trust.md` | [EMERGENT_PHYSICS.md](../../docs/explanation/EMERGENT_PHYSICS.md) |
| `navigator-protocol.md` | [OPERATING_MODEL.md](../../docs/explanation/OPERATING_MODEL.md) |
| `evidence-discipline.md` | [CLAIMS_VS_EVIDENCE.md](../../docs/explanation/CLAIMS_VS_EVIDENCE.md) |
| `pack-check-philosophy.md` | [VALIDATOR_AS_LAW.md](../../docs/explanation/VALIDATOR_AS_LAW.md) |
| `sandbox-and-permissions.md` | [BOUNDARY_PHYSICS.md](../../docs/explanation/BOUNDARY_PHYSICS.md) |

## See Also

- [docs/AGOPS_MANIFESTO.md](../../docs/AGOPS_MANIFESTO.md) - The full AgOps philosophy
- [docs/explanation/META_LEARNINGS.md](../../docs/explanation/META_LEARNINGS.md) - What we learned building this
- [docs/explanation/EMERGENT_PHYSICS.md](../../docs/explanation/EMERGENT_PHYSICS.md) - The 12 laws that emerged
- [docs/explanation/TRUST_COMPILER.md](../../docs/explanation/TRUST_COMPILER.md) - What this system actually is
- [docs/explanation/VALIDATOR_AS_LAW.md](../../docs/explanation/VALIDATOR_AS_LAW.md) - Why pack-check is the constitution
