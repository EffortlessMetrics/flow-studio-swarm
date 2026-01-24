# v3.0 Roadmap: The Intelligent Factory

> **Status:** Active Development
> **Baseline:** v2.4 (Stepwise orchestration, Station Library, Pack system)
> **Philosophy:** Intelligence handles variance; Physics enforces contracts.

This roadmap captures the v3.0 vision: transforming Flow Studio from a "flow execution harness" into a **Self-Driving SDLC**—a Logic Factory that learns, heals, and evolves.

---

## What's New in v3.0

### Implemented Components

These components are built and integrated:

| Component | Location | Purpose |
|-----------|----------|---------|
| **Stepwise Orchestrator** | `swarm/runtime/stepwise/` | Step transaction abstraction with clear I/O contracts |
| **Station Library** | `swarm/runtime/station_library.py` | Station templates with tunable parameters |
| **Pack System** | `swarm/packs/`, `swarm/config/pack_registry.py` | Portable flow + station bundles |
| **MacroNavigator** | `swarm/runtime/macro_navigator.py` | Between-flow routing with constraint DSL |
| **Fact Extraction** | `swarm/runtime/fact_extraction.py` | Structured fact markers from handoffs |
| **Evolution Engine** | `swarm/runtime/evolution.py` | Policy-gated spec patches from Wisdom |
| **Resilient DB** | `swarm/runtime/resilient_db.py` | Journal-first DuckDB with auto-rebuild |
| **Boundary Review API** | `swarm/api/routes/boundary.py` | Aggregated assumptions/decisions/detours |
| **Run Control** | `swarm/tools/flow_studio_ui/src/run_control.ts` | SSE-driven state management |
| **Inventory Counts** | `swarm/tools/flow_studio_ui/src/components/InventoryCounts.ts` | Real-time fact marker dashboard |
| **Security Hardening** | `swarm/tools/flow_studio_ui/`, `tests/` | XSS prevention, shell injection guards, path traversal blocks |

### Architectural Shifts

| Before (v2.x) | After (v3.0) |
|---------------|--------------|
| Single orchestrator manages everything | Cognitive hierarchy: Worker → Finalizer → Navigator → Curator |
| Static flow execution | Dynamic graph traversal with detours |
| Manual context building | ContextPack curation per step |
| Hope-based verification | Forensic scanners (DiffScanner, TestParser) |
| Session history accumulation | Context Reset + Rehydration (fresh sessions, curated handoffs) |
| Fixed flow specs | Self-healing via Wisdom patches |

### V3 GitHub Lifecycle (Synchronous Model)

The v3 architecture integrates GitHub as a synchronous context source woven throughout the flow lifecycle:

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        V3 GitHub Integration Model                        │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Flow 1-2: Signal → Plan                                                 │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  • gh research: fetch issue context, linked PRs, discussions    │    │
│  │  • Sync fetch at step start (blocking)                          │    │
│  │  • Context loaded into ContextPack for downstream steps         │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                              │                                           │
│                              ▼                                           │
│  Flow 3: Build                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  • Create Draft PR early to wake bots (CI, linters, reviewers)  │    │
│  │  • Draft status signals "work in progress, feedback welcome"    │    │
│  │  • Bots run in parallel with implementation                     │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                              │                                           │
│                              ▼                                           │
│  Flow 4: Review                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  • Harvest PR feedback (bot comments, reviewer notes)           │    │
│  │  • Cluster into work items                                      │    │
│  │  • Apply fixes, flip Draft → Ready                              │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                              │                                           │
│                              ▼                                           │
│  Flow 5-7: Gate → Deploy → Wisdom                                        │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  • Gate: Audit receipts, verify policy, recommend merge/bounce  │    │
│  │  • Deploy: Execute merge, verify health, create audit trail     │    │
│  │  • Wisdom: Analyze artifacts, extract learnings, close loops    │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

**Key Properties:**
- **Synchronous fetches:** All GitHub context is fetched at step start, blocking until complete
- **No webhook dependency:** Works entirely with `gh` CLI polling; no server infrastructure required
- **Deterministic context:** Each step sees a snapshot; no mid-step context changes
- **Bot parallelism:** Draft PR strategy lets CI/linters run while Flow 3 continues implementation

### Open World Routing (V3 Capability)

V3 introduces **Open World Routing**—the ability for flows to dynamically spawn, inject, and compose other flows at runtime.

**Core Capabilities:**

| Capability | Description | Example |
|------------|-------------|---------|
| **Flow Injection** | A flow can invoke another flow as a sub-operation | Flow 3 calls Flow 8 (Rebaser) when stale branch detected |
| **Ad-hoc Station Generation** | Navigator can instantiate stations not in the original spec | Generate a "security-scan" station when risk markers exceed threshold |
| **Nested Graph Stack** | Flow invocations form a call stack; each level has its own handoff scope | Flow 3 → Flow 8 → Flow 3 (resume) |

**Implementation Model:**

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Nested Graph Stack Model                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  MacroNavigator maintains a flow stack:                             │
│                                                                     │
│    ┌─────────────┐                                                  │
│    │  Flow 3     │  ← currently executing                           │
│    │  step: 4    │                                                  │
│    └──────┬──────┘                                                  │
│           │ detects stale branch, injects Flow 8                    │
│           ▼                                                         │
│    ┌─────────────┐                                                  │
│    │  Flow 8     │  ← pushed onto stack                             │
│    │  (Rebaser)  │                                                  │
│    └──────┬──────┘                                                  │
│           │ completes, pops from stack                              │
│           ▼                                                         │
│    ┌─────────────┐                                                  │
│    │  Flow 3     │  ← resumes at step 4 with rebased context        │
│    │  step: 4    │                                                  │
│    └─────────────┘                                                  │
│                                                                     │
│  Handoff Scoping:                                                   │
│  - Each stack frame has its own handoff envelope                    │
│  - Parent context available as read-only                            │
│  - Child results merged into parent on pop                          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Constraint DSL Extensions for Open World:**

```python
# Flow injection constraints
"allow flow_injection from build to rebaser"
"never inject into gate"  # gate must be atomic

# Ad-hoc station constraints
"max 3 adhoc_stations per flow"
"adhoc_stations require navigator approval"

# Stack depth limits
"max stack_depth 4"
"require human_approval when stack_depth > 2"
```

**When to Use:**
- **Flow Injection:** When a mid-flow condition requires a complete sub-workflow (not just a detour)
- **Ad-hoc Stations:** When runtime analysis reveals a gap in the planned flow
- **Nested Stacks:** When flows must compose to handle emergent complexity

---

## Release Readiness (v3.0.0)

> **Status:** Complete — All acceptance criteria met
> **Target:** Operator-grade local SDLC harness

### What "Done" Means for v3.0.0

A new user should be able to:
- Start a run from the UI, watch it progress via SSE, inspect artifacts
- Review boundaries (flow + run scope) from the UI using server aggregation
- Stop a run mid-step without corrupting state, inspect stop forensics
- Have CI prevent UI/TS drift and spec/contract drift

---

### 0. Security Hardening ✓

**Goal:** Defense-in-depth against injection attacks across UI and backend.

**Vulnerabilities Addressed:**

| Vector | Location | Mitigation |
|--------|----------|------------|
| **Stored XSS** | `details.ts` innerHTML calls | `escapeHtml()` sanitization on all dynamic content |
| **Shell Injection** | Python subprocess calls | Eliminated `shell=True`; guardrail test prevents regression |
| **Command Injection** | `ClaudeHarnessBackend` | `run_id` sanitization before shell operations |
| **Path Traversal** | Storage layer, SpecManager, RunStateManager | Path validation and canonicalization |

**Tasks:**
- [x] Audit all `innerHTML` assignments in Flow Studio UI
- [x] Apply `escapeHtml()` to: event.status, event.flow, event.note, step_id, routing.reason, agentDescription, filename
- [x] Eliminate `shell=True` from all subprocess calls
- [x] Add guardrail test: `test_no_shell_true_in_codebase.py`
- [x] Validate `run_id` format before use in shell operations
- [x] Implement path traversal checks in storage layer

**Implementation:** Security fixes shipped in PRs #236 (XSS) and #238 (shell injection). Guardrail tests prevent regression.

---

### 1. Event Contract Alignment ✓

**Goal:** Every state transition produces one event. UI should not infer state.

**Minimum Event Set:**
- `step_start` `{flow_key, step_id, station_id}`
- `step_end` `{flow_key, step_id, station_id, status, verified, progress?}`
- `facts_updated` `{flow_key, step_id}`
- `flow_completed` `{flow_key, status}`
- `run_completed` `{status}`
- `run_stopping` / `run_stopped` `{reason?}`
- `run_pausing` / `run_paused`
- `run_resumed`

**Tasks:**
- [x] Make `run_control.ts` emit callbacks (`onRunEvent`, `onFlowCompleted`, `onRunStopped`)
- [x] Wire `step_end` → `InventoryCounts.load()` (debounced)
- [x] Confirm SSE is the spine; polling only for stub backends
- [x] UI subscribes to `run:stopping` and `run:stopped` SSE events

**Implementation:** `run_control.ts` emits callbacks. `client.ts` `eventTypes` array includes `"run:stopping"` and `"run:stopped"`. `run_control.ts` handles these in `handleSSEEvent()`.

### 2. Boundary Review Integration ✓

**Goal:** Boundary review is server-side aggregation, not UI assembly.

**Tasks:**
- [x] On `flow_completed` in normal mode: fetch `/api/runs/{run}/boundary-review?scope=flow&flow_key=...`
- [x] On `run_completed` in autopilot: fetch `/boundary-review?scope=run`
- [x] Fix `_read_all_envelopes()` to include `review` flow
- [x] Make detour detection robust (handles None, non-strings, whitespace, case)

**Implementation:** `boundary.py` API complete. `_extract_detours()` uses robust normalization: `str(routing.get("decision") or "").strip().upper()`.

### 3. Stop Semantics ✓

**Goal:** "Orderly Shutdown" not "Hard Kill."

**Protocol:**
1. Python catches `SIGINT` or Stop button
2. Inject high-priority message: "Finish current write, save to `handoff_partial.json`"
3. Wait 30s (configurable) for cleanup
4. Write `RunState` as `STOPPED` (not `FAILED`)
5. Emit `run_stopped` event

**Backend:**
- [x] `POST /api/runs/{id}/stop` triggers orderly shutdown
- [x] Backend emits `RUN_STOPPING` → `RUN_STOPPED` events
- [x] Backend writes `stop_report.md` with forensics

**UI:**
- [x] `FlowStudioAPI.stopRun()` calls `POST /api/runs/{id}/stop`
- [x] `run_control.ts` Stop button uses `stopRun()` (`cancelRun()` deprecated alias)
- [x] `client.ts` includes `"run:stopping"` and `"run:stopped"` in `eventTypes` array
- [x] `run_control.ts` handles `run_stopping` and `run_stopped` SSE events
- [x] UI has intermediate "stopping" state in state machine and `updateUI()`
- [x] `stop_report_path` stored in state and passed to `onRunStopped` callback

**Implementation:** `client.ts` has `stopRun()` method. `run_control.ts` implements full stop flow with intermediate state, SSE handlers, and callbacks for `onRunStopping`/`onRunStopped`.

### 4. Type Drift Elimination ✓

**Goal:** Single source of truth for TypeScript types.

**Structure:**
- `src/domain.ts` is canonical
- `js/domain.d.ts` is generated at build
- CI fails if `js/domain.d.ts` is dirty after build

**Tasks:**
- [x] Add `npm run ts-build` target that emits declarations
- [x] Add CI check for dirty declarations
- [x] Remove duplicate type definitions

**Implementation:** `package.json` has `ts-build` script. CI workflow `check-ui-drift` job rebuilds TS and verifies `js/` directory matches committed state.

---

## Near-Term Features (v3.1)

### Accessibility (a11y) Improvements ✓

**Goal:** WCAG 2.1 Level AA compliance for Flow Studio UI.

**Completed:**
- [x] Skip-to-content link for keyboard navigation (WCAG 2.4.1 Bypass Blocks)
- [x] Decorative icons hidden from screen readers (`aria-hidden="true"`)
- [x] Semantic buttons for profile badge, legend toggle, header controls
- [x] ARIA attributes on tab components and modals
- [x] Keyboard shortcuts modal with close button
- [x] `.fs-icon-button` utility class for consistent icon button styling

**Remaining:**
- [ ] Color contrast audit (WCAG 1.4.3)
- [ ] Focus indicator visibility improvements
- [ ] Screen reader testing with NVDA/VoiceOver

### Context Curator Station

**Goal:** Separate "where to go" from "what to pack."

A dedicated station that outputs:
- `context_pack.json` (file pointers, short summaries, active assumptions)
- `context_digest.md` (human-readable)
- `context_budget.json` (what was excluded + why)

**Rationale:** Navigator decides direction; Curator decides cargo. This prevents mega-context growth.

### Enhanced Forensic Scanners

**Goal:** Higher signal-to-noise in DiffScanner output.

**Improvements:**
- Filter lockfiles, build artifacts, IDE settings
- Highlight semantic changes (function signatures, exports)
- Track file ownership (who touched what)

### Inventory Deltas in Boundary Review

**Goal:** Show what changed since last boundary.

**Additions to `/boundary-review`:**
- Marker totals
- Deltas since last boundary (or last step)
- Flow boundary: delta from first step → last step in flow

---

## Medium-Term Vision (v3.2+)

### Flow 8: The Rebaser

**Purpose:** Reconcile stale Shadow Fork with updated upstream.

**Behavior:**
1. Read completed run artifacts from Shadow Fork
2. Fetch current `upstream/main`
3. Attempt automated rebase
4. If conflicts: generate conflict resolution suggestions
5. Output: rebased branch or conflict report

**Rationale:** "Always Finish" policy means we often have valuable work in a diverged branch. Flow 8 recovers that value.

### Constraint DSL Expansion

**Current Patterns:**
- `"never {action} unless {condition}"`
- `"max {N} {action_type}"`
- `"require {action} after {flow}"`

**Proposed Additions:**
- `"prefer {path_a} over {path_b} when {condition}"`
- `"escalate to human after {N} failures"`
- `"checkpoint state every {N} steps"`

### Multi-Run Analysis

**Goal:** Wisdom across runs, not just within.

**Features:**
- Pattern detection across last N runs
- Regression trend analysis
- Station performance benchmarks

---

## V4 Vision: Async Context Mesh

> **Status:** Future roadmap item. **Not required for public release.**
> This section captures architectural thinking for a post-v3 evolution.

V3's synchronous GitHub model (fetch-at-step-start) works well for single-developer, single-machine workflows. V4 envisions an **Async Context Mesh**—a continuously updating context layer that enables flows to react to external events without blocking.

### The Problem V4 Solves

In V3, context is a snapshot:
- Step starts → fetch GitHub state → execute with that snapshot
- If a reviewer comments mid-step, the agent doesn't see it until next step
- If CI fails during Flow 3, the agent continues unaware until Flow 4

V4 enables **streaming context awareness** without requiring agents to poll.

### Async Context Mesh Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          V4: Async Context Mesh                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  External Sources                    Event Bus                              │
│  ┌─────────────┐                    ┌─────────────────────────────────────┐ │
│  │ GitHub      │───webhook─────────▶│                                     │ │
│  │ Webhooks    │                    │     Event Ingestion Layer           │ │
│  └─────────────┘                    │                                     │ │
│  ┌─────────────┐                    │  • Normalize events to ContextFact  │ │
│  │ CI Systems  │───webhook─────────▶│  • Deduplicate and filter noise     │ │
│  │ (Actions)   │                    │  • Route to relevant run contexts   │ │
│  └─────────────┘                    │                                     │ │
│  ┌─────────────┐                    └──────────────┬──────────────────────┘ │
│  │ Slack/Teams │───webhook─────────▶               │                        │
│  │ (optional)  │                                   │                        │
│  └─────────────┘                                   ▼                        │
│                                     ┌─────────────────────────────────────┐ │
│                                     │     Async Enrichment Layer          │ │
│                                     │                                     │ │
│                                     │  • Background LLM threads interpret │ │
│                                     │    new info ("What does this mean   │ │
│                                     │    for the current task?")          │ │
│                                     │  • Priority scoring for urgency     │ │
│                                     │  • Conflict detection               │ │
│                                     │                                     │ │
│                                     └──────────────┬──────────────────────┘ │
│                                                    │                        │
│                                                    ▼                        │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                         ContextPack (Enhanced)                          ││
│  │                                                                         ││
│  │  At step start, ContextPack pulls "latest relevant GitHub facts":      ││
│  │                                                                         ││
│  │  • Baseline context (same as V3)                                        ││
│  │  • + New facts since last step (webhook-derived)                        ││
│  │  • + Enrichment summaries ("CI failed on lint, see line 42")            ││
│  │  • + Priority markers ("URGENT: reviewer requested changes")            ││
│  │                                                                         ││
│  │  Agent sees consolidated view, not raw event stream                     ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### V4 Components

| Component | Purpose | Complexity |
|-----------|---------|------------|
| **Event Bus** | Webhook ingestion, normalization, routing | Medium (needs hosting) |
| **Async Enrichment Threads** | Optional LLM calls to interpret incoming events | High (cost, latency) |
| **Enhanced ContextPack** | Pulls "latest relevant GH facts" at step start | Medium (query logic) |
| **Priority Scorer** | Determines if new info warrants interruption | Medium |
| **Conflict Detector** | Identifies when new info invalidates in-progress work | High |

### V4 vs V3 Comparison

| Aspect | V3 (Synchronous) | V4 (Async Mesh) |
|--------|------------------|-----------------|
| Context freshness | Snapshot at step start | Continuously updated |
| Infrastructure | Zero (gh CLI only) | Webhook server, event bus |
| Latency to new info | Up to full flow duration | Seconds to minutes |
| Cost | LLM calls only | LLM + hosting + enrichment threads |
| Complexity | Low | High |
| Dependency | None | Webhook infrastructure |

### Why V4 is Not Required for Public Release

1. **V3 is sufficient for target users:** Single developers and small teams working on focused tasks don't need sub-minute context freshness.

2. **Infrastructure burden:** V4 requires a server to receive webhooks, adding hosting complexity that conflicts with "zero infrastructure" positioning.

3. **Cost multiplication:** Async enrichment threads could multiply LLM costs significantly for marginal benefit.

4. **Complexity/value ratio:** The added complexity of conflict detection and priority scoring may not justify the benefit for most workflows.

**V4 becomes valuable when:**
- Multiple agents work on the same codebase simultaneously
- Flows run for hours and external state changes frequently
- Real-time collaboration between humans and agents is required
- Enterprise deployments with dedicated infrastructure teams

### Migration Path (V3 to V4)

V4 is designed as an additive layer:
- V3 flows continue to work unchanged
- Event Bus is opt-in per repository
- Async enrichment is configurable (off by default)
- ContextPack maintains backward compatibility

---

## Architecture Evolution

### Phase Completion Status

| Phase | Status | Description |
|-------|--------|-------------|
| **Phase 0** | Complete | Teaching repo, hand-maintained adapters |
| **Phase 1** | Complete | Machine-readable config (`swarm/config/`, registries) |
| **Phase 2** | Complete | Single-platform generation (`gen_adapters.py`) |
| **Phase 3** | In Progress | Multi-platform + self-healing specs |

### v3.0 Layer Model

```
┌─────────────────────────────────────────────────────────────┐
│                     UI Layer (Flow Studio)                  │
│  - SSE-driven state                                         │
│  - Boundary Review modals                                   │
│  - Inventory Counts dashboard                               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      API Layer (FastAPI)                    │
│  - /runs, /events, /boundary, /facts, /evolution            │
│  - SSE streaming                                            │
│  - Resilient DB queries                                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Runtime Layer (Python)                    │
│  - StepwiseOrchestrator (step transactions)                 │
│  - MacroNavigator (between-flow routing)                    │
│  - Navigator (within-flow routing)                          │
│  - FactExtraction (marker system)                           │
│  - Evolution (spec patches)                                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Storage Layer (Journal-First)              │
│  - events.jsonl (append-only ledger)                        │
│  - DuckDB (projection, auto-rebuild)                        │
│  - Handoff envelopes (step outputs)                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Engine Layer (LLM Execution)               │
│  - Claude SDK Runner                                        │
│  - Claude CLI Runner                                        │
│  - Gemini CLI (for comparison)                              │
│  - Stub Engine (for testing)                                │
└─────────────────────────────────────────────────────────────┘
```

---

## Acceptance Criteria for v3.0.0

Run this checklist to verify alignment:

1. **SSE → Inventory Refresh** ✓
   - [x] Start server + UI
   - [x] Start a run from UI
   - [x] Confirm `step_start/step_end` stream in SSE
   - [x] Confirm InventoryCounts updates within ~1s of `step_end`

2. **Boundary Review Flow** ✓
   - [x] `flow_completed` shows "Review available" (normal mode)
   - [x] Autopilot shows boundary only at plan end
   - [x] Boundary review fetched from endpoint, not assembled in UI

3. **Stop Semantics** ✓
   - [x] Backend: `POST /api/runs/{id}/stop` exists and works
   - [x] Backend: Emits `run:stopping` → `run:stopped` events
   - [x] Backend: Writes `stop_report.md` with forensics
   - [x] UI: Stop button calls `stopRun()` which uses POST /stop
   - [x] UI: Subscribes to `run:stopping` and `run:stopped` SSE events
   - [x] UI: Has intermediate "stopping" state distinct from "stopped"
   - [x] UI: Stores `stop_report_path` and passes to `onRunStopped` callback

4. **Resilient DB** ✓
   - [x] Delete DuckDB file
   - [x] UI still works (degraded)
   - [x] `/api/db/health` shows `needs_rebuild`
   - [x] `/api/db/rebuild` restores projection

5. **CI Reliability** ✓
   - [x] Guardrail tests don't fail on unrelated PRs (vendor SDK check is now path-filtered)
   - [x] Vendor artifact regen is deterministic or gated (confirmed in audit; gen scripts are deterministic)
   - [x] Clean PR doesn't fail for historical reasons (integration test masking fixed; cross-PR docs added)

6. **Security Hardening** ✓
   - [x] XSS prevention: All `innerHTML` calls sanitized via `escapeHtml()` in details.ts
   - [x] Shell injection prevention: `shell=True` eliminated from subprocess calls
   - [x] Guardrail test prevents reintroduction of `shell=True`
   - [x] Command injection: `run_id` sanitization in ClaudeHarnessBackend
   - [x] Path traversal: Validation in SpecManager, RunStateManager, storage layer

---

## Out of Scope for v3.0

Explicitly deferred:

- Multi-tenant / hosted mode
- Real-time collaboration features
- Non-Python orchestration runtime
- Breaking changes to existing flow specs
- Automated deployment (Flow 5 remains human-gated)

---

## Migration Notes

### From v2.4 to v3.0

1. **Pack System:** Flows are now defined in `swarm/packs/flows/*.json`. Legacy `swarm/config/flows/*.yaml` is still supported but packs are preferred.

2. **Station Library:** Agent configs now live in `swarm/packs/stations/*.yaml` with tunable parameters.

3. **Event Contract:** If you have custom UI integrations, update to listen for the new event types.

4. **Resilient DB:** The database auto-rebuilds. If you were manually managing the DB file, this is now handled automatically.

---

## Contributing

See [docs/AGOPS_MANIFESTO.md](./AGOPS_MANIFESTO.md) for the operational philosophy.

Items will be prioritized based on:
1. Alignment with the core trade: **spend compute to save senior engineer attention**
2. Reduction of "context drunkenness" and "hallucination" risk
3. Improvement of forensic visibility and auditability
