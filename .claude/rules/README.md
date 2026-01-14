# AgOps Rules Registry

This directory contains the governance rules for Flow Studio's agentic operations.
These rules encode Steven Zimmerman's AI-native development philosophy: **trade compute for senior attention**.

> Voice and communication style: see `communication/voice-and-tone.md`.

## Rule Categories

| Directory | Purpose | Enforcement |
|-----------|---------|-------------|
| `governance/` | Agent behavioral contracts, trust equations, calibration | Agent prompts + validation |
| `execution/` | Context budgets, routing decisions, error handling | Runtime kernel |
| `artifacts/` | Receipt schemas, handoff protocols, observability | `receipt_io.py` + validation |
| `safety/` | Git safety, secrets, incident response, permissions | Hooks + boundary agents |
| `communication/` | Documentation philosophy, messaging, voice | Human review |

## Core Principle

**Rules are constitution; docs are textbook.**

- Rules define what MUST happen (enforced)
- Docs explain WHY it happens (teaching)
- Pack-check validates COMPETENCE, not schema compliance

## The Physics Stack

Rules encode the "physics" that make autonomous operation safe:

1. **Truth Hierarchy** - Physics beats narrative (exit codes > claims)
2. **Session Amnesia** - Each step starts fresh; disk is memory
3. **Mechanical Truth** - Never ask models to judge success; measure it
4. **Contained Blast Radius** - Destructive inside sandbox; gated at boundary
5. **Bounded Routing** - Kernel generates candidates; Navigator selects; kernel validates
6. **Narrow Trust** - Scope narrowness × evidence quality × verification depth

When physics conflict, higher principles win. See [Physics Enforcement Hierarchy](#physics-enforcement-hierarchy) below.

---

## Physics Enforcement Hierarchy

| Priority | Principle | When Conflicts Arise |
|----------|-----------|---------------------|
| 1 | **Truth Hierarchy** | Physics beats narrative. Trust exit codes, not claims. |
| 2 | **Boundary Physics** | Internal failures are routing signals; publish gates are hard stops. |
| 3 | **Evidence Discipline** | Evidence must exist AND be fresh. "Not measured" is valid. |
| 4 | **Narrow Trust** | Broad claims require more evidence than narrow claims. |
| 5 | **Session Amnesia** | Disk is memory; chat is ephemeral. Load from artifacts, not history. |

---

## Rule Registry

### Governance (`governance/`)

| Rule | Purpose |
|------|---------|
| `agent-behavioral-contracts.md` | Role families, status reporting, PM/IC model |
| `agent-composition-*.md`, `agent-when-*.md` | Composition patterns, single vs multiple agent decisions |
| `anti-patterns-*.md` | Anti-pattern catalogs (agent, flow, evidence, economic) |
| `budget-discipline.md` | The $30 run, cost allocation |
| `calibration-*.md` | Learning loop, signals, improvement process |
| `deprecation-*.md` | Sunset stages, migration requirements |
| `evidence-discipline.md` | Sheriff pattern, what counts as evidence |
| `factory-model.md` | Kernel as foreman, agents as interns |
| `fix-forward-vocabulary.md` | BLOCKED is rare, valid outcomes |
| `flow-charters.md` | Goals, exit criteria, non-goals per flow |
| `forensics-over-testimony.md` | Routing on evidence, not claims |
| `model-policy.md` | Model allocation by role family |
| `narrow-trust.md` | Trust equation |
| `pack-check-philosophy.md` | Competence over compliance |
| `panel-thinking.md` | Anti-Goodhart multi-metric panels |
| `prompt-*.md` | Prompt structure, banned patterns, required patterns |
| `reviewer-protocol.md` | Three questions, review protocols |
| `runbook-*.md` | Runbook structure, validation, standards |
| `scarcity-enforcement.md` | Token budgets, two-reasons spawning |
| `tests-*.md`, `test-*.md` | Tests as evidence, test anti-patterns |
| `truth-hierarchy.md` | Evidence levels |
| `versioning-*.md` | Schemes, compatibility, migration |

### Execution (`execution/`)

| Rule | Purpose |
|------|---------|
| `circuit-breaker.md` | Cascade failure prevention |
| `context-discipline.md` | Session amnesia, rehydration |
| `detour-catalog.md` | Known fix patterns |
| `error-*.md` | Classification, handling, aggregation |
| `handoff-*.md` | Patterns, examples, protocol |
| `microloop-rules.md` | Exit conditions, fuse detection |
| `navigator-protocol.md` | Forensics → decision → validation |
| `resume-protocol.md` | Checkpoint semantics |
| `retry-policy.md` | Backoff strategies |
| `routing-decisions.md` | Decision vocabulary |
| `subsumption-principle.md` | Kernel compensates for backend gaps |
| `timeout-policy.md` | Timeout hierarchy |
| `token-*.md` | Token budgets, compression, waste patterns |

### Artifacts (`artifacts/`)

| Rule | Purpose |
|------|---------|
| `artifact-naming.md` | Predictable naming conventions |
| `capability-registry.md` | Evidence binding for capabilities |
| `data-retention-*.md` | Lifecycle, exceptions, privacy |
| `handoff-protocol.md` | Envelope structure |
| `observability-*.md` | Schema, content, placement |
| `off-road-logging.md` | Routing decision audit trail |
| `receipt-schema.md` | Required fields for audit |
| `scent-trail.md` | Decision provenance |
| `teaching-notes-contract.md` | Required sections for instructions |

### Safety (`safety/`)

| Rule | Purpose |
|------|---------|
| `boundary-automation.md` | Publish gate enforcement |
| `commit-standards.md` | Atomic, traceable commits |
| `pr-standards.md` | PR descriptions, evidence |
| `dependency-*.md` | Dependency intake, patterns, policy |
| `git-safety.md` | Shadow fork model |
| `incident-*.md` | Response protocol, failed runs, stuck runs, wrong output |
| `rollback-*.md` | Rollback types, prevention, recovery |
| `sandbox-and-permissions.md` | Containment model |
| `secret-*.md` | Categories, storage, rotation, detection, response |

### Communication (`communication/`)

| Rule | Purpose |
|------|---------|
| `documentation-philosophy.md` | README structure, proof before philosophy |
| `paradigm-messaging.md` | Historical framing, transition narrative |
| `trust-thesis.md` | Code is cheap, trust is expensive |
| `voice-and-tone.md` | Industrial voice, concrete over abstract |

---

## FR-XXX Validation Mapping

| FR Rule | Physics Enforced | Implementing Rules |
|---------|------------------|-------------------|
| FR-001 | Narrow Trust | `agent-behavioral-contracts.md`, `narrow-trust.md` |
| FR-002, FR-002b | Narrow Trust | `agent-behavioral-contracts.md`, `model-policy.md` |
| FR-003, FR-FLOWS | Bounded Routing | `flow-charters.md`, `routing-decisions.md` |
| FR-005 | Session Amnesia | `receipt-schema.md`, `handoff-protocol.md` |
| FR-006, FR-006a | Mechanical Truth | `microloop-rules.md`, `fix-forward-vocabulary.md` |
| FR-007 | Truth Hierarchy | `capability-registry.md`, `evidence-discipline.md` |

---

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
