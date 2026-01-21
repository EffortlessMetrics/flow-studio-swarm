// swarm/tools/flow_studio_ui/src/run_history.ts
// Run History panel module for Flow Studio
//
// This module handles:
// - Loading and displaying run history
// - Run filtering (all, example, active)
// - Run selection from history
// - Run detail modal/panel display
import { Api } from "./api.js";
import { state, STATUS_ICONS } from "./state.js";
import { escapeHtml, formatDateTime } from "./utils.js";
import { getDefaultRunHistoryFilter } from "./teaching_mode.js";
let _callbacks = {};
/**
 * Configure callbacks for the run history module.
 * Call this before using other functions to wire up UI interactions.
 */
export function configure(callbacks = {}) {
    _callbacks = { ..._callbacks, ...callbacks };
}
const _state = {
    runs: [],
    filteredRuns: [],
    currentFilter: "all",
    selectedRunId: null,
    isLoading: false,
    error: null,
    // Pagination defaults
    total: 0,
    limit: 100,
    offset: 0,
    hasMore: false,
};
// ============================================================================
// Run History Loading
// ============================================================================
/**
 * Load run history from API and update internal state.
 * Fetches runs from the API and populates the run history panel.
 */
export async function loadRunHistory() {
    _state.isLoading = true;
    _state.error = null;
    try {
        const data = await Api.getRuns();
        _state.runs = data.runs || [];
        // Store pagination info from API response
        _state.total = data.total ?? _state.runs.length;
        _state.limit = data.limit ?? 100;
        _state.offset = data.offset ?? 0;
        _state.hasMore = data.has_more ?? false;
        applyFilter(_state.currentFilter);
        _state.isLoading = false;
    }
    catch (err) {
        console.error("Failed to load run history", err);
        _state.runs = [];
        _state.filteredRuns = [];
        _state.error = "Failed to load runs";
        _state.isLoading = false;
    }
}
// ============================================================================
// Filtering and Ordering
// ============================================================================
/**
 * Curated runs that should appear first in the list.
 * These are the "golden" demo runs that are most useful for demos/teaching.
 */
const CURATED_RUNS_ORDER = [
    "stepwise-stub",
    "stepwise-sdlc-stub",
    "stepwise-sdlc-claude",
    "demo-health-check",
    "health-check",
    "health-check-risky-deploy",
];
/**
 * Sort runs with curated runs first, then by created_at descending.
 */
function sortRuns(runs) {
    return [...runs].sort((a, b) => {
        const idxA = CURATED_RUNS_ORDER.indexOf(a.run_id);
        const idxB = CURATED_RUNS_ORDER.indexOf(b.run_id);
        // Both are curated: sort by curated order
        if (idxA !== -1 && idxB !== -1) {
            return idxA - idxB;
        }
        // Only A is curated: A comes first
        if (idxA !== -1)
            return -1;
        // Only B is curated: B comes first
        if (idxB !== -1)
            return 1;
        // Neither curated: sort examples before active, then by created_at descending
        if (a.run_type === "example" && b.run_type !== "example")
            return -1;
        if (a.run_type !== "example" && b.run_type === "example")
            return 1;
        // Same type: sort by created_at descending (newest first)
        const dateA = a.created_at ?? "";
        const dateB = b.created_at ?? "";
        return dateB.localeCompare(dateA);
    });
}
/**
 * Apply filter to runs and update filtered list.
 */
function applyFilter(type) {
    _state.currentFilter = type;
    let filtered;
    switch (type) {
        case "example":
            filtered = _state.runs.filter(r => r.run_type === "example");
            break;
        case "active":
            filtered = _state.runs.filter(r => r.run_type === "active");
            break;
        case "all":
        default:
            filtered = [..._state.runs];
            break;
    }
    // Apply curated-first sorting
    _state.filteredRuns = sortRuns(filtered);
}
/**
 * Filter the displayed runs by type.
 *
 * @param type - Filter type: "all", "example", or "active"
 */
export function filterRuns(type) {
    applyFilter(type);
    // Update filter button UI
    const filterContainer = document.getElementById("run-history-filter");
    if (filterContainer) {
        filterContainer.querySelectorAll(".filter-btn").forEach(btn => {
            const filter = btn.dataset.filter;
            const isActive = filter === type;
            btn.classList.toggle("active", isActive);
            btn.setAttribute("aria-pressed", isActive ? "true" : "false");
        });
    }
    // Re-render if we have a container (for panel mode)
    const container = document.querySelector('[data-uiid="flow_studio.sidebar.run_history"]');
    if (container instanceof HTMLElement) {
        renderRunHistoryPanel(container);
    }
    // Re-render list items (for integrated mode)
    renderRunListItems();
}
// ============================================================================
// Run Selection
// ============================================================================
/**
 * Handle run selection from history.
 * Updates internal state and calls the onRunSelect callback.
 *
 * @param runId - The ID of the run to select
 */
export async function selectHistoryRun(runId) {
    _state.selectedRunId = runId;
    // Update UI to reflect selection
    updateSelectionUI(runId);
    // Notify consumer
    if (_callbacks.onRunSelect) {
        await _callbacks.onRunSelect(runId);
    }
}
/**
 * Update the UI to reflect the currently selected run.
 */
function updateSelectionUI(runId) {
    // Remove active class from all items
    document.querySelectorAll(".run-history-item").forEach(el => {
        el.classList.remove("active");
    });
    // Add active class to selected item
    const selectedItem = document.querySelector(`[data-uiid="flow_studio.sidebar.run_history.item:${runId}"]`);
    if (selectedItem) {
        selectedItem.classList.add("active");
    }
}
// ============================================================================
// Run Detail
// ============================================================================
/**
 * Open the run detail modal/panel for a specific run.
 *
 * @param runId - The ID of the run to show details for
 */
export async function openRunDetail(runId) {
    if (_callbacks.onRunDetailOpen) {
        await _callbacks.onRunDetailOpen(runId);
    }
}
// ============================================================================
// HTML Rendering Helpers
// ============================================================================
/**
 * Get display name for a run.
 */
function getRunDisplayName(run) {
    return run.title || run.run_id;
}
/**
 * Get human-readable backend label.
 */
function getBackendLabel(backendId) {
    const labels = {
        "claude-harness": "Claude",
        "claude-agent-sdk": "Claude SDK",
        "claude-step-orchestrator": "Claude Stepwise",
        "gemini-cli": "Gemini",
        "gemini-step-orchestrator": "Gemini Stepwise",
        "custom-cli": "Custom",
    };
    return labels[backendId] || backendId;
}
/**
 * Get run type badge HTML.
 */
function getRunTypeBadge(run) {
    const badges = [];
    // Add type badge (example or active)
    const isExample = run.run_type === "example";
    const typeBadgeClass = isExample ? "run-history-item-badge example" : "run-history-item-badge active";
    const typeLabel = isExample ? "Example" : "Active";
    badges.push(`<span class="${typeBadgeClass}" data-uiid="flow_studio.sidebar.run_history.item.badge.${run.run_type}:${escapeHtml(run.run_id)}">${typeLabel}</span>`);
    // Add backend badge if present
    if (run.backend) {
        const backendLabel = getBackendLabel(run.backend);
        badges.push(`<span class="run-history-item-badge backend" data-uiid="flow_studio.sidebar.run_history.item.badge.backend:${escapeHtml(run.run_id)}">${escapeHtml(backendLabel)}</span>`);
    }
    // Add exemplar badge if marked
    if (run.is_exemplar) {
        badges.push(`<span class="run-history-item-badge exemplar" data-uiid="flow_studio.sidebar.run_history.item.badge.exemplar:${escapeHtml(run.run_id)}">Exemplar</span>`);
    }
    return badges.join(" ");
}
/**
 * Get run status indicator based on run summary.
 * This checks the global state for run status data.
 */
function getRunStatusIndicator(runId) {
    // Check if we have status data for this run
    if (state.currentRunId === runId && state.runStatus.flows) {
        // Determine overall status from flows
        const flowStatuses = Object.values(state.runStatus.flows);
        const hasError = flowStatuses.some(f => f.status === "missing");
        const hasWarning = flowStatuses.some(f => f.status === "partial" || f.status === "in_progress");
        const allComplete = flowStatuses.every(f => f.status === "done" || f.status === "complete");
        if (hasError) {
            return `<span class="run-status-indicator error" title="Has errors">${STATUS_ICONS.missing}</span>`;
        }
        else if (hasWarning) {
            return `<span class="run-status-indicator warning" title="In progress">${STATUS_ICONS.partial}</span>`;
        }
        else if (allComplete) {
            return `<span class="run-status-indicator ok" title="Complete">${STATUS_ICONS.done}</span>`;
        }
    }
    // Default: unknown status (bullet)
    return `<span class="run-status-indicator unknown" title="Status unknown">\u2022</span>`;
}
/**
 * Render a single run history item.
 *
 * @param run - The run to render
 * @returns HTML string for the run history item
 */
function renderRunHistoryItem(run) {
    const displayName = escapeHtml(getRunDisplayName(run));
    const typeBadge = getRunTypeBadge(run);
    const statusIndicator = getRunStatusIndicator(run.run_id);
    const timestamp = run.created_at ? formatDateTime(run.created_at) : "";
    const description = run.description ? escapeHtml(run.description) : "";
    const isActive = _state.selectedRunId === run.run_id ? " active" : "";
    return `
    <div
      class="run-history-item${isActive}"
      data-uiid="flow_studio.sidebar.run_history.item:${escapeHtml(run.run_id)}"
      data-run-id="${escapeHtml(run.run_id)}"
      role="option"
      aria-selected="${_state.selectedRunId === run.run_id}"
      tabindex="0"
    >
      <div class="run-history-item-header">
        ${statusIndicator}
        <span class="run-history-item-title">${displayName}</span>
        ${typeBadge}
      </div>
      ${timestamp ? `<div class="run-history-item-meta fs-text-xs muted">${timestamp}</div>` : ""}
      ${description ? `<div class="run-history-item-desc fs-text-xs muted">${description}</div>` : ""}
    </div>
  `;
}
/**
 * Render the full run history list.
 *
 * @param runs - Array of runs to render
 * @returns HTML string for the run history list
 */
function renderRunHistoryList(runs) {
    if (runs.length === 0) {
        return renderRunHistoryEmpty();
    }
    const items = runs.map(run => renderRunHistoryItem(run)).join("");
    return `
    <div class="run-history-list" role="listbox" aria-label="Run history">
      ${items}
    </div>
  `;
}
/**
 * Render empty state for run history.
 *
 * @returns HTML string for empty state
 */
function renderRunHistoryEmpty() {
    const filterText = _state.currentFilter === "all"
        ? "No runs available"
        : `No ${_state.currentFilter} runs`;
    return `
    <div class="fs-empty run-history-empty">
      <div class="fs-empty-icon">\u{1F4C2}</div>
      <p class="fs-empty-title">${filterText}</p>
      <p class="fs-empty-description">
        ${_state.currentFilter === "all"
        ? "Generate example data to explore Flow Studio."
        : `Try changing the filter or run <code class="mono fs-text-xs">make demo-run</code>`}
      </p>
      ${_state.currentFilter === "all" ? '<code class="mono fs-empty-command">make demo-run</code>' : ""}
    </div>
  `;
}
/**
 * Render loading state.
 */
function renderRunHistoryLoading() {
    return `
    <div class="run-history-loading muted">
      Loading runs...
    </div>
  `;
}
/**
 * Render error state.
 */
function renderRunHistoryError(error) {
    return `
    <div class="fs-error run-history-error">
      <div class="fs-error-icon">\u26A0\uFE0F</div>
      <p class="fs-error-title">Error loading runs</p>
      <p class="fs-error-description">${escapeHtml(error)}</p>
      <button class="fs-error-action" data-action="retry-load">Retry</button>
    </div>
  `;
}
/**
 * Render filter tabs.
 */
function renderFilterTabs() {
    const filters = ["all", "example", "active"];
    const labels = {
        all: "All",
        example: "Examples",
        active: "Active",
    };
    const tabs = filters.map(filter => {
        const isActive = _state.currentFilter === filter ? " active" : "";
        return `<span class="tab${isActive}" data-filter="${filter}">${labels[filter]}</span>`;
    }).join("");
    return `<div class="run-history-filters tabs">${tabs}</div>`;
}
/**
 * Render pagination info when there are more runs available.
 */
function renderPaginationInfo() {
    // Only show if we have runs and there might be more
    if (_state.runs.length === 0)
        return "";
    const shown = _state.runs.length;
    const total = _state.total;
    // If we're showing all runs, just show the count
    if (!_state.hasMore && shown === total) {
        return `<div class="run-pagination-info muted fs-text-xs">${total} runs</div>`;
    }
    // Show pagination info when there are more
    return `
    <div class="run-pagination-info muted fs-text-xs">
      Showing ${shown} of ${total} runs
      ${_state.hasMore ? `<span class="pagination-hint">(use CLI: <code>make runs-list-v</code>)</span>` : ""}
    </div>
  `;
}
// ============================================================================
// Panel Rendering
// ============================================================================
/**
 * Render the run history panel into a container element.
 *
 * @param container - The HTML element to render into
 */
export function renderRunHistoryPanel(container) {
    let content;
    if (_state.isLoading) {
        content = renderRunHistoryLoading();
    }
    else if (_state.error) {
        content = renderRunHistoryError(_state.error);
    }
    else {
        content = renderRunHistoryList(_state.filteredRuns);
    }
    container.innerHTML = `
    <div class="run-history-panel" data-uiid="flow_studio.sidebar.run_history">
      <div class="run-history-header">
        <h3 class="run-history-title">Run History</h3>
        ${renderFilterTabs()}
      </div>
      <div class="run-history-content">
        ${content}
      </div>
      ${renderPaginationInfo()}
    </div>
  `;
    // Attach event listeners
    attachEventListeners(container);
}
/**
 * Attach event listeners to the rendered panel.
 */
function attachEventListeners(container) {
    // Filter tab clicks
    container.querySelectorAll("[data-filter]").forEach(tab => {
        tab.addEventListener("click", () => {
            const filter = tab.dataset.filter;
            filterRuns(filter);
        });
    });
    // Run item clicks
    container.querySelectorAll(".run-history-item").forEach(item => {
        item.addEventListener("click", () => {
            const runId = item.dataset.runId;
            if (runId) {
                void selectHistoryRun(runId);
            }
        });
        // Keyboard support
        item.addEventListener("keydown", (e) => {
            if (e instanceof KeyboardEvent && (e.key === "Enter" || e.key === " ")) {
                e.preventDefault();
                const runId = item.dataset.runId;
                if (runId) {
                    void selectHistoryRun(runId);
                }
            }
        });
    });
    // Retry button click
    const retryBtn = container.querySelector('[data-action="retry-load"]');
    if (retryBtn) {
        retryBtn.addEventListener("click", () => {
            void loadRunHistory().then(() => {
                renderRunHistoryPanel(container);
            });
        });
    }
}
// ============================================================================
// Public Accessors
// ============================================================================
/**
 * Get the currently selected run ID.
 */
export function getSelectedRunId() {
    return _state.selectedRunId;
}
/**
 * Get the current filter type.
 */
export function getCurrentFilter() {
    return _state.currentFilter;
}
/**
 * Get the current runs (filtered).
 */
export function getFilteredRuns() {
    return [..._state.filteredRuns];
}
/**
 * Get all loaded runs.
 */
export function getAllRuns() {
    return [..._state.runs];
}
/**
 * Set the selected run ID without triggering callback.
 * Useful for syncing with external state changes.
 */
export function setSelectedRunId(runId) {
    _state.selectedRunId = runId;
    if (runId) {
        updateSelectionUI(runId);
    }
}
// ============================================================================
// Initialization
// ============================================================================
/**
 * Render run list items into the existing #run-history-list container.
 * This works with the pre-existing HTML structure in index.html.
 */
function renderRunListItems() {
    const listContainer = document.getElementById("run-history-list");
    if (!listContainer)
        return;
    if (_state.isLoading) {
        listContainer.innerHTML = renderRunHistoryLoading();
        return;
    }
    if (_state.error) {
        listContainer.innerHTML = renderRunHistoryError(_state.error);
        // Attach retry handler
        const retryBtn = listContainer.querySelector('[data-action="retry-load"]');
        if (retryBtn) {
            retryBtn.addEventListener("click", () => {
                void initRunHistory();
            });
        }
        return;
    }
    if (_state.filteredRuns.length === 0) {
        listContainer.innerHTML = renderRunHistoryEmpty();
        return;
    }
    // Render run items
    listContainer.innerHTML = _state.filteredRuns.map(run => renderRunHistoryItem(run)).join("");
    // Attach click handlers to run items
    listContainer.querySelectorAll(".run-history-item").forEach(item => {
        item.addEventListener("click", () => {
            const runId = item.dataset.runId;
            if (runId) {
                void selectHistoryRun(runId);
            }
        });
        // Keyboard support
        item.addEventListener("keydown", (e) => {
            if (e instanceof KeyboardEvent && (e.key === "Enter" || e.key === " ")) {
                e.preventDefault();
                const runId = item.dataset.runId;
                if (runId) {
                    void selectHistoryRun(runId);
                }
            }
        });
    });
}
/**
 * Initialize run history handlers on the existing HTML structure.
 * This wires up the filter buttons and collapse toggle that already exist in index.html.
 */
function initRunHistoryHandlers() {
    // Wire up filter buttons
    const filterContainer = document.getElementById("run-history-filter");
    if (filterContainer) {
        filterContainer.querySelectorAll(".filter-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                const filter = btn.dataset.filter;
                if (!filter)
                    return;
                // Update active state on buttons with aria-selected
                filterContainer.querySelectorAll(".filter-btn").forEach(b => {
                    b.classList.remove("active");
                    b.setAttribute("aria-selected", "false");
                });
                btn.classList.add("active");
                btn.setAttribute("aria-selected", "true");
                // Apply filter and re-render
                applyFilter(filter);
                renderRunListItems();
            });
        });
    }
    // Wire up collapse toggle
    const toggleBtn = document.getElementById("run-history-toggle");
    const listContainer = document.getElementById("run-history-list");
    if (toggleBtn && listContainer) {
        toggleBtn.addEventListener("click", () => {
            const isExpanded = toggleBtn.getAttribute("aria-expanded") === "true";
            toggleBtn.setAttribute("aria-expanded", isExpanded ? "false" : "true");
            toggleBtn.textContent = isExpanded ? "\u25B6" : "\u25BC"; // Right arrow when collapsed, down arrow when expanded
            listContainer.classList.toggle("collapsed", isExpanded);
        });
    }
}
/**
 * Initialize the run history panel.
 * Loads runs from the API and populates the existing HTML structure.
 *
 * Call this once during app initialization to:
 * - Load initial run data
 * - Wire up filter buttons
 * - Wire up collapse toggle
 * - Render the run list
 *
 * When Teaching Mode is enabled, defaults to "example" filter.
 */
export async function initRunHistory() {
    // Initialize handlers (only need to do this once, but it's idempotent)
    initRunHistoryHandlers();
    // Set initial filter based on Teaching Mode
    const defaultFilter = getDefaultRunHistoryFilter();
    _state.currentFilter = defaultFilter;
    // Update filter button UI to match
    const filterContainer = document.getElementById("run-history-filter");
    if (filterContainer) {
        filterContainer.querySelectorAll(".filter-btn").forEach(btn => {
            const filter = btn.dataset.filter;
            const isActive = filter === defaultFilter;
            btn.classList.toggle("active", isActive);
            btn.setAttribute("aria-pressed", isActive ? "true" : "false");
        });
    }
    // Load and render
    await loadRunHistory();
    renderRunListItems();
}
