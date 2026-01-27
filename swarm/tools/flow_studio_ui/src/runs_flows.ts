// swarm/tools/flow_studio_ui/src/runs_flows.ts
// Run + flow orchestration for Flow Studio
//
// This module handles:
// - Run loading and selection (loadRuns, loadRunStatus)
// - Flow loading and selection (loadFlows, setActiveFlow)
// - SDLC bar updates (updateSDLCBar)
// - Flow list status (updateFlowListStatus)
// - Graph status overlays (updateGraphStatus)
// - Run comparison (setCompareRun, loadComparison)

import { state, STATUS_ICONS, FLOW_STATUS_META } from "./state.js";
import { FLOW_KEYS, FLOW_TITLES } from "./flow_constants.js";
import { Api } from "./api.js";
import { renderGraphCore } from "./graph.js";
import { renderFlowOutline } from "./graph_outline.js";
import { getTeachingMode } from "./teaching_mode.js";
import type {
  FlowKey,
  FlowDetail,
  FlowStep,
  NodeData,
  Run,
  Flow,
  RunsFlowsCallbacks,
  StepStatus,
  FlowHealthStatus,
  FlowStatusData,
  WisdomSummary,
} from "./domain.js";

// ============================================================================
// Wisdom Status Types
// ============================================================================

/**
 * Wisdom status for SDLC bar indicator.
 * - ok: wisdom exists, no regressions
 * - warning: wisdom exists, has warnings or non-blocking issues
 * - error: wisdom exists, has regressions
 * - unknown: no wisdom data available
 */
export type WisdomIndicatorStatus = "ok" | "warning" | "error" | "unknown";

import {
  renderNoRuns,
  renderNoFlows,
  renderRunsLoadError,
} from "./ui_fragments.js";

// Cached wisdom summary for current run
let _cachedWisdomSummary: WisdomSummary | null = null;
let _wisdomLoadPromise: Promise<WisdomSummary | null> | null = null;

// ============================================================================
// Canvas empty state management
// ============================================================================

/**
 * Show or hide the canvas empty state based on whether we have data.
 * Called when runs/flows are loaded or cleared.
 */
export function updateCanvasEmptyState(hasRuns: boolean): void {
  const emptyState = document.getElementById("canvas-empty-state");
  if (!emptyState) return;
  emptyState.style.display = hasRuns ? "none" : "flex";
}

// ============================================================================
// Module configuration - callbacks set by consumer
// ============================================================================

let _onFlowDetails: ((detail: FlowDetail) => void) | null = null;
let _onNodeClick: ((nodeData: NodeData) => void) | null = null;
let _onURLUpdate: (() => void) | null = null;
let _updateFlowListGovernance: (() => void) | null = null;

/**
 * Configure callbacks for the runs/flows module.
 * Call this before using other functions to wire up UI interactions.
 */
export function configure(callbacks: RunsFlowsCallbacks = {}): void {
  if (callbacks.onFlowDetails) _onFlowDetails = callbacks.onFlowDetails;
  if (callbacks.onNodeClick) _onNodeClick = callbacks.onNodeClick;
  if (callbacks.onURLUpdate) _onURLUpdate = callbacks.onURLUpdate;
  if (callbacks.updateFlowListGovernance) _updateFlowListGovernance = callbacks.updateFlowListGovernance;
}

// ============================================================================
// Flow Health Status
// ============================================================================

/**
 * Map flow status data to a simplified health status for sidebar display.
 * This provides a consistent mental model: ok, warning, error, unknown.
 *
 * @param flowData - The flow status data from the run summary, or undefined if no data
 * @returns FlowHealthStatus - The simplified health status
 */
export function getFlowHealthStatus(flowData: FlowStatusData | undefined): FlowHealthStatus {
  // No data means unknown
  if (!flowData) {
    return "unknown";
  }

  const status = flowData.status;

  // Map StepStatus to FlowHealthStatus
  switch (status) {
    case "done":
    case "complete":
      return "ok";

    case "partial":
    case "in_progress":
      return "warning";

    case "missing":
      return "error";

    case "not_started":
    case "n/a":
    default:
      return "unknown";
  }
}

// ============================================================================
// Run Management
// ============================================================================

/**
 * Helper to get display name for a run.
 */
function getRunDisplayName(run: Run): string {
  return run.title || run.run_id;
}

/**
 * Load runs into the run selector and initialize state.currentRunId.
 * Also caches runs for compare selector and loads initial run status.
 */
export async function loadRuns(): Promise<Run[]> {
  try {
    const data = await Api.getRuns();
    const runs = data.runs || [];
    const selector = document.getElementById("run-selector") as HTMLSelectElement | null;
    if (!selector) return runs;

    selector.innerHTML = "";

    if (!runs.length) {
      selector.innerHTML = '<option value="">No runs available</option>';
      // Show empty state hint in sidebar
      const listEl = document.getElementById("flow-list");
      if (listEl) {
        listEl.innerHTML = renderNoRuns();
      }
      // Show canvas empty state
      updateCanvasEmptyState(false);
      return runs;
    }

    // Hide canvas empty state since we have runs
    updateCanvasEmptyState(true);

    // Group by type
    const examples = runs.filter(r => r.run_type === "example");
    const active = runs.filter(r => r.run_type === "active");

    if (examples.length) {
      const optgroup = document.createElement("optgroup");
      optgroup.label = "Examples";
      examples.forEach(run => {
        const opt = document.createElement("option");
        opt.value = run.run_id;
        opt.textContent = getRunDisplayName(run);
        opt.title = run.description || "";
        optgroup.appendChild(opt);
      });
      selector.appendChild(optgroup);
    }

    if (active.length) {
      const optgroup = document.createElement("optgroup");
      optgroup.label = "Active Runs";
      active.forEach(run => {
        const opt = document.createElement("option");
        opt.value = run.run_id;
        opt.textContent = getRunDisplayName(run);
        opt.title = run.description || "";
        optgroup.appendChild(opt);
      });
      selector.appendChild(optgroup);
    }

    // Default to first example or first run
    state.currentRunId = examples.length ? examples[0].run_id : runs[0].run_id;
    selector.value = state.currentRunId;

    // Cache runs for compare selector
    state.availableRuns = runs;
    updateCompareSelector();

    // Load run status
    await loadRunStatus();

    return runs;
  } catch (err) {
    console.error("Failed to load runs", err);
    const selector = document.getElementById("run-selector") as HTMLSelectElement | null;
    if (selector) {
      selector.innerHTML = '<option value="">Error loading runs</option>';
    }
    // Show error state in sidebar
    const listEl = document.getElementById("flow-list");
    if (listEl) {
      listEl.innerHTML = renderRunsLoadError();
    }
    // Show canvas empty state on error
    updateCanvasEmptyState(false);
    return [];
  }
}

/**
 * Load summary for current run and update SDLC + flow list + graph status.
 */
export async function loadRunStatus(): Promise<void> {
  if (!state.currentRunId) return;

  try {
    const data = await Api.getRunSummary(state.currentRunId);
    state.runStatus = data || {};
    updateSDLCBar();
    updateFlowListStatus();

    if (state.currentFlowKey && state.cy) {
      updateGraphStatus();
      // Refresh outline since status labels may have changed
      renderFlowOutline();
    }
  } catch (err) {
    console.error("Failed to load run status", err);
    state.runStatus = {};
  }
}

/**
 * Update the compare run selector dropdown.
 */
export function updateCompareSelector(): void {
  const compareSelector = document.getElementById("compare-selector") as HTMLSelectElement | null;
  if (!compareSelector) return;

  compareSelector.innerHTML = '<option value="">None</option>';

  const examples = state.availableRuns.filter(r => r.run_type === "example" && r.run_id !== state.currentRunId);
  const active = state.availableRuns.filter(r => r.run_type === "active" && r.run_id !== state.currentRunId);

  if (examples.length) {
    const optgroup = document.createElement("optgroup");
    optgroup.label = "Examples";
    examples.forEach(run => {
      const opt = document.createElement("option");
      opt.value = run.run_id;
      opt.textContent = getRunDisplayName(run);
      opt.title = run.description || "";
      optgroup.appendChild(opt);
    });
    compareSelector.appendChild(optgroup);
  }

  if (active.length) {
    const optgroup = document.createElement("optgroup");
    optgroup.label = "Active Runs";
    active.forEach(run => {
      const opt = document.createElement("option");
      opt.value = run.run_id;
      opt.textContent = getRunDisplayName(run);
      opt.title = run.description || "";
      optgroup.appendChild(opt);
    });
    compareSelector.appendChild(optgroup);
  }

  // Clear invalid compare run
  if (state.compareRunId && !state.availableRuns.find(r => r.run_id === state.compareRunId && r.run_id !== state.currentRunId)) {
    state.compareRunId = null;
    state.comparisonData = null;
  } else if (state.compareRunId) {
    compareSelector.value = state.compareRunId;
  }
}

/**
 * Load comparison data between current and compare runs.
 */
export async function loadComparison(): Promise<void> {
  if (!state.compareRunId || !state.currentFlowKey || !state.currentRunId) {
    state.comparisonData = null;
    return;
  }

  try {
    state.comparisonData = await Api.compareRuns({
      runA: state.currentRunId,
      runB: state.compareRunId,
      flow: state.currentFlowKey
    });
    updateSDLCBar();
  } catch (err) {
    console.error("Failed to load comparison", err);
    state.comparisonData = null;
  }
}

/**
 * Set comparison run and load comparison data.
 */
export async function setCompareRun(runId: string | null): Promise<void> {
  state.compareRunId = runId || null;
  state.comparisonData = null;

  if (state.compareRunId && state.currentFlowKey) {
    await loadComparison();
  } else {
    updateSDLCBar();
  }
}

/**
 * Render comparison table HTML from state.comparisonData.
 */
export function renderComparisonTable(): string {
  if (!state.comparisonData) return "";

  const summary = state.comparisonData.summary || { improved: 0, regressed: 0, unchanged: 0 };
  const steps = state.comparisonData.steps || [];
  const statusIcons: Record<string, string> = { complete: "\u2705", partial: "\u26a0\ufe0f", missing: "\u274c", "n/a": "\u2014" };
  const changeIndicators: Record<string, { arrow: string; cls: string }> = {
    improved: { arrow: "\u2191", cls: "arrow-improved" },
    regressed: { arrow: "\u2193", cls: "arrow-regressed" },
    unchanged: { arrow: "\u2192", cls: "arrow-unchanged" }
  };

  const rows = steps.map(s => {
    const iconA = statusIcons[s.run_a.status] || "\u2014";
    const iconB = statusIcons[s.run_b.status] || "\u2014";
    const ch = changeIndicators[s.change] || changeIndicators.unchanged;
    return `<tr><td>${s.step_id}</td><td>${iconA} ${s.run_a.status}</td><td>${iconB} ${s.run_b.status}</td><td class="${ch.cls}">${ch.arrow} ${s.change}</td></tr>`;
  }).join("");

  return `
    <div class="compare-summary">
      <span class="compare-summary-item change-improved">\u2191 ${summary.improved || 0} improved</span>
      <span class="compare-summary-item change-regressed">\u2193 ${summary.regressed || 0} regressed</span>
      <span class="compare-summary-item change-unchanged">\u2192 ${summary.unchanged || 0} unchanged</span>
    </div>
    <table class="comparison-table">
      <thead><tr><th>Step</th><th>Run A (${state.comparisonData.run_a})</th><th>Run B (${state.comparisonData.run_b})</th><th>Change</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

// ============================================================================
// SDLC Bar
// ============================================================================

/**
 * Load wisdom summary for the current run (with caching).
 * Returns null if no wisdom data is available.
 */
async function loadWisdomSummary(): Promise<WisdomSummary | null> {
  if (!state.currentRunId) {
    _cachedWisdomSummary = null;
    return null;
  }

  // Return cached if available
  if (_cachedWisdomSummary && _cachedWisdomSummary.run_id === state.currentRunId) {
    return _cachedWisdomSummary;
  }

  // Avoid duplicate requests
  if (_wisdomLoadPromise) {
    return _wisdomLoadPromise;
  }

  _wisdomLoadPromise = (async () => {
    try {
      const wisdom = await Api.getRunWisdom(state.currentRunId!);
      _cachedWisdomSummary = wisdom;
      return wisdom;
    } catch {
      // 404 or other error - no wisdom available
      _cachedWisdomSummary = null;
      return null;
    } finally {
      _wisdomLoadPromise = null;
    }
  })();

  return _wisdomLoadPromise;
}

/**
 * Determine wisdom indicator status from wisdom summary.
 */
function getWisdomIndicatorStatus(wisdom: WisdomSummary | null): WisdomIndicatorStatus {
  if (!wisdom) {
    return "unknown";
  }

  // Check for regressions
  if (wisdom.summary.regressions_found > 0) {
    return "error";
  }

  // Check for any failed flows or issues
  const hasFailedFlows = Object.values(wisdom.flows).some(f => f.status === "failed");
  if (hasFailedFlows || wisdom.summary.issues_created > 0) {
    return "warning";
  }

  return "ok";
}

/**
 * Get CSS class for wisdom indicator dot.
 */
function getWisdomIndicatorClass(status: WisdomIndicatorStatus): string {
  const classes: Record<WisdomIndicatorStatus, string> = {
    ok: "wisdom-indicator--ok",
    warning: "wisdom-indicator--warning",
    error: "wisdom-indicator--error",
    unknown: "wisdom-indicator--unknown",
  };
  return classes[status] || classes.unknown;
}

/**
 * Get tooltip text for wisdom indicator.
 */
function getWisdomIndicatorTooltip(status: WisdomIndicatorStatus, wisdom: WisdomSummary | null): string {
  switch (status) {
    case "ok":
      return `Wisdom: ${wisdom?.summary.learnings_count || 0} learnings, no regressions`;
    case "warning":
      return `Wisdom: ${wisdom?.summary.issues_created || 0} issues created`;
    case "error":
      return `Wisdom: ${wisdom?.summary.regressions_found || 0} regressions found`;
    case "unknown":
    default:
      return "Wisdom: No data available";
  }
}

/**
 * Clear cached wisdom data (called when run changes).
 */
export function clearWisdomCache(): void {
  _cachedWisdomSummary = null;
  _wisdomLoadPromise = null;
}

/**
 * Update SDLC bar with run + comparison status.
 */
export function updateSDLCBar(): void {
  const container = document.getElementById("sdlc-flows");
  if (!container) return;

  container.innerHTML = "";

  FLOW_KEYS.forEach((key, idx) => {
    if (idx > 0) {
      const arrow = document.createElement("span");
      arrow.className = "sdlc-arrow";
      arrow.textContent = "\u2192";
      container.appendChild(arrow);
    }

    const flowData = state.runStatus.flows?.[key];
    const status = (flowData?.status || "not_started") as StepStatus;
    const icon = STATUS_ICONS[status] || "\u2014";

    const el = document.createElement("span");
    el.className = "sdlc-flow" + (key === state.currentFlowKey ? " active" : "");
    el.dataset.key = key;
    el.innerHTML = `<span class="icon">${icon}</span> ${FLOW_TITLES[key]}`;
    el.addEventListener("click", () => setActiveFlow(key));
    container.appendChild(el);
  });

  // Add wisdom indicator after the SDLC bar flows
  renderWisdomIndicator(container);
}

/**
 * Render wisdom indicator dot in SDLC bar.
 * Shows status of wisdom data availability and health.
 */
async function renderWisdomIndicator(container: HTMLElement): Promise<void> {
  // Create placeholder element
  const indicatorWrapper = document.createElement("span");
  indicatorWrapper.className = "wisdom-indicator-wrapper";
  indicatorWrapper.setAttribute("data-uiid", "flow_studio.sdlc_bar.wisdom_indicator");
  container.appendChild(indicatorWrapper);

  // Load wisdom data asynchronously
  const wisdom = await loadWisdomSummary();
  const status = getWisdomIndicatorStatus(wisdom);

  // Skip rendering if no data and run has no completed wisdom flow
  const wisdomFlowData = state.runStatus.flows?.wisdom;
  if (status === "unknown" && (!wisdomFlowData || wisdomFlowData.status === "not_started")) {
    indicatorWrapper.style.display = "none";
    return;
  }

  const indicatorClass = getWisdomIndicatorClass(status);
  const tooltip = getWisdomIndicatorTooltip(status, wisdom);

  indicatorWrapper.innerHTML = `
    <span class="wisdom-indicator ${indicatorClass}" title="${tooltip}" aria-label="${tooltip}">
      <span class="wisdom-indicator__dot"></span>
    </span>
  `;
  indicatorWrapper.style.display = "inline-flex";
}

// ============================================================================
// Flow List
// ============================================================================

/**
 * Update list items in the sidebar with status icons and tooltips.
 * Uses FlowHealthStatus for a consistent user-facing status model.
 */
export function updateFlowListStatus(): void {
  const items = document.querySelectorAll(".flow-item");
  items.forEach(item => {
    const key = (item as HTMLElement).dataset.key as FlowKey | undefined;
    if (!key) return;

    const flowData = state.runStatus.flows?.[key];
    const healthStatus = getFlowHealthStatus(flowData);
    const meta = FLOW_STATUS_META[healthStatus];

    let iconEl = item.querySelector(".flow-status-icon") as HTMLSpanElement | null;
    if (!iconEl) {
      iconEl = document.createElement("span");
      iconEl.className = "flow-status-icon";
      iconEl.setAttribute("aria-hidden", "true");
      item.insertBefore(iconEl, item.firstChild);
    }

    iconEl.textContent = meta.icon;
    iconEl.title = meta.tooltip;
  });
}

/**
 * Load flows and populate the flow list sidebar.
 */
export async function loadFlows(): Promise<Flow[]> {
  const data = await Api.getFlows();
  const flows = data.flows || [];
  const listEl = document.getElementById("flow-list");
  if (!listEl) return flows;

  listEl.innerHTML = "";

  if (!flows.length) {
    listEl.innerHTML = renderNoFlows();
    return flows;
  }

  flows.forEach(flow => {
    const item = document.createElement("div");
    item.className = "flow-item";
    item.dataset.key = flow.key;

    // Initialize with "unknown" status (bullet dot + tooltip)
    const unknownMeta = FLOW_STATUS_META.unknown;
    const iconEl = document.createElement("span");
    iconEl.className = "flow-status-icon";
    iconEl.setAttribute("aria-hidden", "true");
    iconEl.textContent = unknownMeta.icon;
    iconEl.title = unknownMeta.tooltip;

    const content = document.createElement("div");
    content.className = "flow-item-content";

    const title = document.createElement("div");
    title.className = "flow-title";
    title.textContent = flow.title || flow.key;

    const sub = document.createElement("div");
    sub.className = "flow-sub";
    sub.textContent = `${flow.step_count} step(s)`;

    content.appendChild(title);
    content.appendChild(sub);
    item.appendChild(iconEl);
    item.appendChild(content);

    item.addEventListener("click", () => {
      setActiveFlow(flow.key);
    });

    listEl.appendChild(item);
  });

  // Update status icons if we have run data
  if (state.runStatus.flows) {
    updateFlowListStatus();
  }

  // Update governance badges if configured
  if (_updateFlowListGovernance) {
    _updateFlowListGovernance();
  }

  // Select the first flow by default
  if (flows.length) {
    await setActiveFlow(flows[0].key);
  }

  return flows;
}

/**
 * Mark active flow in sidebar and SDLC bar.
 */
export function markActiveFlow(flowKey: FlowKey): void {
  // Update sidebar flow list
  document.querySelectorAll(".flow-item").forEach(el => {
    el.classList.toggle("active", (el as HTMLElement).dataset.key === flowKey);
  });

  // Update SDLC bar
  document.querySelectorAll(".sdlc-flow").forEach(el => {
    el.classList.toggle("active", (el as HTMLElement).dataset.key === flowKey);
  });
}

// ============================================================================
// Graph Status
// ============================================================================

/**
 * Update Cytoscape nodes with run status (step badges).
 */
export function updateGraphStatus(): void {
  if (!state.cy || !state.currentFlowKey || !state.runStatus.flows) return;

  const flowData = state.runStatus.flows[state.currentFlowKey];
  if (!flowData || !flowData.steps) return;

  // Update step nodes with status badges
  state.cy.nodes('[type = "step"]').forEach(node => {
    const stepId = node.data("step_id") as string | undefined;
    if (!stepId) return;
    const stepData = flowData.steps[stepId];
    if (!stepData) return;

    const status = (stepData.status || "n/a") as StepStatus;
    const icon = STATUS_ICONS[status] || "";
    const label = node.data("label") as string;

    // Update label to include status icon
    if (!label.startsWith(icon)) {
      (node as unknown as { data(key: string, value: string): void }).data("label", `${icon} ${label.replace(/^[\u2705\u26a0\ufe0f\u274c\u2014] /, "")}`);
    }
  });
}

// ============================================================================
// Teaching Mode Highlights
// ============================================================================

/**
 * Update Cytoscape nodes with teaching highlights.
 * When Teaching Mode is enabled, steps with teaching_highlight: true get
 * a visual emphasis (border color/style).
 *
 * @param detail - The flow detail containing step info with teaching_highlight
 */
export function updateGraphTeachingHighlights(detail: FlowDetail): void {
  if (!state.cy || !getTeachingMode()) return;

  const stepsWithHighlight = new Set<string>();
  (detail.steps || []).forEach((step: FlowStep) => {
    if (step.teaching_highlight) {
      stepsWithHighlight.add(step.id);
    }
  });

  // Apply teaching highlight style to marked steps
  state.cy.nodes('[type = "step"]').forEach(node => {
    const stepId = node.data("step_id") as string | undefined;
    if (!stepId) return;

    if (stepsWithHighlight.has(stepId)) {
      // Add teaching highlight class - styled via Cytoscape
      (node as unknown as { addClass(cls: string): void }).addClass("teaching-highlight");
    } else {
      (node as unknown as { removeClass(cls: string): void }).removeClass("teaching-highlight");
    }
  });
}

/**
 * Clear all teaching highlights from the graph.
 * Called when teaching mode is disabled.
 */
export function clearGraphTeachingHighlights(): void {
  if (!state.cy) return;

  state.cy.nodes('[type = "step"]').forEach(node => {
    (node as unknown as { removeClass(cls: string): void }).removeClass("teaching-highlight");
  });
}

// ============================================================================
// Flow Selection and Graph Loading
// ============================================================================

/**
 * Load flow graph based on current view mode.
 */
async function loadFlowGraph(flowKey: FlowKey): Promise<void> {
  let graph;
  if (state.currentViewMode === "artifacts") {
    graph = await Api.getFlowGraphArtifacts(flowKey, state.currentRunId || undefined);
  } else {
    graph = await Api.getFlowGraphAgents(flowKey);
  }
  const detail = await Api.getFlowDetail(flowKey);

  // Render graph with node click handler
  renderGraphCore(graph, { onNodeClick: _onNodeClick || undefined });

  // Call flow details callback
  if (_onFlowDetails) {
    _onFlowDetails(detail);
  }

  // Update graph with run status after rendering
  if (state.runStatus.flows) {
    updateGraphStatus();
  }

  // Update teaching highlights if Teaching Mode is on
  updateGraphTeachingHighlights(detail);

  // Update semantic outline after graph render (for accessibility/LLM agents)
  renderFlowOutline();
}

/**
 * Set the active flow, load its graph + detail, and refresh status overlays.
 */
export async function setActiveFlow(flowKey: FlowKey, force = false): Promise<void> {
  if (state.currentFlowKey === flowKey && !force) return;

  state.currentFlowKey = flowKey;
  markActiveFlow(flowKey);

  // Update URL for shareable links
  if (_onURLUpdate) {
    _onURLUpdate();
  }

  // Load graph using view-mode-aware function
  await loadFlowGraph(flowKey);
}

// ============================================================================
// Refresh Helpers
// ============================================================================

/**
 * Refresh the current flow's graph (e.g., after view mode change).
 */
export async function refreshCurrentFlow(): Promise<void> {
  if (state.currentFlowKey) {
    await loadFlowGraph(state.currentFlowKey);
  }
}

/**
 * Refresh all run-related state (run status, SDLC bar, flow list, graph).
 */
export async function refreshRunState(): Promise<void> {
  await loadRunStatus();
  if (state.currentFlowKey) {
    await loadFlowGraph(state.currentFlowKey);
  }
}
