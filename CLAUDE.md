# Flow Studio operating map

Flow Studio visualizes and evaluates agentic engineering methods. It contains
historical demo flows, generated topology, runtime backends, UI contracts and
provider adapters. It is not itself the authority for every product repository's
live PR, review, check, merge or release state.

The current method is [docs/CURRENT_SDLC_METHOD.md](docs/CURRENT_SDLC_METHOD.md).
Issue [#1463](https://github.com/EffortlessMetrics/flow-studio-swarm/issues/1463)
tracks migration of the YAML/runtime/UI and behavioral evaluations. The portable
Claude pack lives in
[demo-swarm](https://github.com/EffortlessMetrics/demo-swarm); its source and
release lifecycle remain separate.

## Authority and evidence

Accepted product direction governs what work should become. Current source and
evidence govern what we can claim. GitHub owns live issue, PR, review, check and
merge facts. Git owns versioned source and decisions. Worker environments own
unpublished bytes, processes, caches and warm build state.

`swarm/runs/<run-id>/` is a retained local observation surface. If an expected
record is absent, the local harness has not captured it; that does not prove a
remote GitHub effect never occurred. Read the native owner before retrying or
reconstructing work.

Receipts and evidence help a reviewer inspect what happened. They are not the
product, universal correctness, merge permission or release authority. Preserve
actual source, producer, command, executed subjects, outcome and limitations.
A hash authenticates none of those facts by itself.

## Current lifecycle

```text
problem and consumer
-> challenged plan and falsifier
-> warm implementation, focused proof and repair
-> differentiated substantive review
-> explicit qualification request for the selected current candidate
-> mandatory plus justified risk-directed proof
-> separate current product/repository/integration judgment
-> protected expected-head merge and landed reconciliation
```

Questions can recur and readers can work concurrently. Keep one mutation writer
per candidate. Agent names and generated steps are available implementations,
not a mandatory fresh-agent conveyor or a fixed clean-pass count.

Ordinary commit, push, Draft and Ready are publication/review operations in the
target design. Ready is not the CI request. A request for one head cannot be
inherited by a successor. Qualification success does not merge. Merge does not
authorize a tag, GitHub Release, package publication, source promotion or
production deployment.

No routine auto-merge or merge queue is part of the selected normal flow. The
normal complete active qualification target is at most 20 minutes; queue time and
shifted warm-session work are reported separately. Ordinary main health requires
both one hour and ten merges since its accepted baseline.

## Repository layers

| Layer | Path | Meaning |
|---|---|---|
| Current method | `docs/CURRENT_SDLC_METHOD.md` | Normative lifecycle interpretation |
| Flow configuration | `swarm/config/flows/` | Existing generated/demo topology; migration pending |
| Flow prose | `swarm/flows/` | Human contract and compatibility notes |
| Runbooks | `swarm/runbooks/` | Bounded operating procedures |
| Runtime | `swarm/runtime/` | Harness execution and retained observations |
| UI | `swarm/tools/flow_studio_ui/` | Visualization and governed SDK/UIID surface |
| Provider adapter | `.claude/` | Claude-specific entrypoints and workers |
| Run evidence | `swarm/runs/<run-id>/` | Local observations, not live GitHub authority |

The generated Mermaid/step tables show the currently configured demo topology.
Until #1463 migrates the config/runtime/renderer, do not infer that every step is
mandatory, that its actor is exclusive, or that its terminal word authorizes the
next privileged effect. Historical runs remain historical evidence.

## Working in the repository

Start from the issue or existing PR and current `main`. Search for an active
writer before opening another candidate. Enter at the earliest missing or stale
useful judgment. Preserve unrelated work and use one coherent acceptance and
rollback claim per PR.

When changing flow configuration or generated surfaces:

```bash
make gen-flows
make gen-flow-constants
make gen-adapters
make gen-index-html
make check-flows
make check-flow-constants
make check-adapters
make check-index-html
make validate-swarm
```

Use the smallest applicable subset during development and the repository's
current full validation before integration. Generated files are changed through
their source generators, not by hand.

General validation:

```bash
make dev-check
make test-gating
make docs-check
```

The repository's current Actions still run on ordinary PR/push events. That is
installed behavior, not evidence that the target late-qualification migration is
complete. Do not disable it or claim a cutover from documentation alone.

## Flow Studio UI

Wait for `html[data-ui-ready="ready"]`. Use the governed SDK and UIIDs:

```javascript
window.__flowStudio.getState()
window.__flowStudio.setActiveFlow("build")
window.__flowStudio.selectStep("build", "1")
```

```text
[data-uiid="flow_studio.header.search.input"]
[data-uiid="flow_studio.sidebar.flow_list"]
[data-uiid^="flow_studio.canvas.outline.step:"]
```

Edit UI fragments under `swarm/tools/flow_studio_ui/fragments/` and regenerate
`index.html`; do not hand-edit generated output. Update tests when changing the
SDK, UIID or compiled TypeScript contract.

## Completion

Separate product learning, source/change delivery, released/installed delivery
and improvement of the method. A generated graph, valid receipt or completed
agent turn proves only its bounded claim. Record the loaded method/harness,
information presented, observed action and tested correction before claiming a
behavioral improvement.
