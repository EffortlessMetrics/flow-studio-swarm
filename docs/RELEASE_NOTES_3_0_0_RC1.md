# v3.0.0-rc.1 Release Notes

> **Release Date:** January 18, 2026
>
> This release introduces the V3 Core Architecture, featuring the Stepwise Orchestrator,
> Pack System, MacroNavigator, and a resilient journal-first database.

---

## v3.0.0-rc.1: The Intelligent Factory

**v3.0.0-rc.1 is a major architectural upgrade** transforming Flow Studio from a flow harness into a self-driving SDLC platform.

Key transitions in this release:
- **From Scripts to Orchestrator:** Intelligent `StepwiseOrchestrator` manages transactions.
- **From Static Routing to Open World:** `MacroNavigator` enables dynamic flow injection and ad-hoc station generation.
- **From Fixed Specs to Packs:** Portable `swarm/packs/` bundles for modular composition.
- **From Polling to Streaming:** FastAPI + SSE architecture for real-time observability.

### Announcement (Copy-Paste Ready)

> **Flow Studio v3.0.0-rc.1** brings the "Intelligent Factory" model to life.
>
> It features a cognitive hierarchy where **Workers** implement, **Finalizers** summarize,
> **Navigators** route, and **Curators** pack context. This structure enables "context sharding,"
> keeping agents focused and hallucination-free even in long-running flows.
>
> New capabilities include: Stepwise Orchestration, Open World Routing, Resilient DB,
> and the portable Pack System.
>
> See the [ROADMAP_3_0.md](ROADMAP_3_0.md) for the full vision.

---

## Stability Matrix

| Surface | Status | Notes |
|---------|--------|-------|
| **Pack System** | ⚠️ Beta | Primary way to define flows; `swarm/config` legacy support remains |
| **Stepwise Contract** | ✅ Stable | Transaction invariants locked |
| **MacroNavigator DSL** | ⚠️ Beta | Constraint language evolving |
| **Resilient DB** | ✅ Stable | Auto-rebuild from `events.jsonl` |
| **Flow Studio API** | ✅ Stable | FastAPI implementation |
| **Validation Rules** | ✅ Stable | V3 extensions added |

---

## Highlights

### V3 Core Architecture
- **Stepwise Orchestrator**: High-trust, intelligence-driven orchestration with per-step transactions.
- **Pack System**: Portable flow and station bundles (`swarm/packs/`) for modular swarm composition.
- **MacroNavigator**: Between-flow routing with constraint DSL and flow stack support.
- **Open World Routing**: Support for flow injection (e.g., auto-rebase during Build) and ad-hoc station generation.
- **Cognitive Hierarchy**: Evolution from simple agents to Worker → Finalizer → Navigator → Curator roles.

### Infrastructure & Persistence
- **Resilient Database**: Journal-first DuckDB with auto-rebuild from append-only `events.jsonl` ledger.
- **Boundary Review API**: Aggregated endpoint for reviewing assumptions, decisions, and detours.
- **Inventory Counts**: Real-time fact marker extraction and visualization in Flow Studio.
- **Claude Agent SDK Modernization**: Full integration with the latest Anthropic Agent SDK and tool-use patterns.

### Safety & Governance
- **Orderly Shutdown**: Support for graceful interruption and `handoff_partial.json` persistence.
- **Memory Pushdown**: Protocol modernization and documentation refactor for reduced context bloat.
- **Spec-First Integration**: Modular validation for flow and station contracts.

---

## Changes

### New Flow: Flow 8 (Reset/Rebase)
A dedicated flow for reconciling stale branches with upstream/main. It demonstrates the **Flow Injection** capability, where the Build flow can summon Flow 8 to fix a diverge and then resume building.

### Infrastructure Modernization
- **FastAPI Upgrade**: Backend fully modernized with FastAPI and SSE-driven state management.
- **Validation Framework**: Upgraded validator supporting FR-001 through FR-005 with V3 extensions.
- **Handoff Protocol**: Standardized handoff envelopes with forensic evidence and explicit unknowns.

---

## Upgrade Notes

### From v2.4 (or v2.3.x)

1. **Pack System Adoption**:
   - Flows are now defined in `swarm/packs/flows/*.json`. 
   - Legacy `swarm/config/flows/*.yaml` is still supported but packs are preferred.
   - Run `make validate-swarm` to ensure your pack configs are valid.

2. **Station Library**:
   - Agent configs now live in `swarm/packs/stations/*.yaml` with tunable parameters.
   - Adjust your `AGENTS.md` or local configs if you customized station parameters.

3. **Event Contract**:
   - If you have custom UI integrations, update to listen for the new event types (e.g., `step_start`, `step_end`, `facts_updated`).

4. **Resilient DB**:
   - The database now auto-rebuilds from `events.jsonl`.
   - If you were manually managing the `.duckdb` file, you can stop; `make selftest-doctor` or the runtime will handle it.

---

## See Also

- [ARCHITECTURE.md](../ARCHITECTURE.md): Full V3 system architecture
- [ROADMAP_3_0.md](ROADMAP_3_0.md): Vision and next steps
- [STEPWISE_BACKENDS.md](STEPWISE_BACKENDS.md): Stepwise execution details
