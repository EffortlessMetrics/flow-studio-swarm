// swarm/tools/flow_studio_ui/src/ui_fragments.ts
// Reusable HTML fragments for Flow Studio UI
//
// This module provides helper functions for common UI patterns:
// - Empty states (no data available)
// - Error states (loading failures)
// - Key-value displays
// - Mode-specific hints (author vs operator)
import { escapeHtml, createCopyButton } from "./utils.js";
// ============================================================================
// Empty States
// ============================================================================
/**
 * Render an empty state for "no runs" in the sidebar.
 */
export function renderNoRuns() {
    const container = document.createElement("div");
    container.className = "fs-empty";
    container.style.padding = "16px 12px";
    const icon = document.createElement("div");
    icon.className = "fs-empty-icon";
    icon.textContent = "\u{1F4C2}";
    const title = document.createElement("p");
    title.className = "fs-empty-title";
    title.textContent = "No runs yet";
    const desc = document.createElement("p");
    desc.className = "fs-empty-description";
    desc.textContent = "Generate example data to explore Flow Studio.";
    const cmdContainer = document.createElement("div");
    cmdContainer.style.display = "flex";
    cmdContainer.style.alignItems = "center";
    cmdContainer.style.justifyContent = "center";
    cmdContainer.style.marginTop = "12px";
    const code = document.createElement("code");
    code.className = "mono fs-empty-command";
    code.textContent = "make demo-run";
    const btn = createCopyButton("make demo-run");
    cmdContainer.appendChild(code);
    cmdContainer.appendChild(btn);
    container.appendChild(icon);
    container.appendChild(title);
    container.appendChild(desc);
    container.appendChild(cmdContainer);
    return container;
}
/**
 * Render an empty state for "no flows configured" in the sidebar.
 */
export function renderNoFlows() {
    return `
    <div class="fs-empty" style="padding: 16px 12px;">
      <div class="fs-empty-icon">\u{1F527}</div>
      <p class="fs-empty-title">No flows configured</p>
      <p class="fs-empty-description">Add flow configs to <code class="mono fs-text-xs">swarm/config/flows/</code></p>
    </div>
  `;
}
/**
 * Render the "select a node" empty state for the details panel.
 * Includes onboarding content explaining flows, steps, and agents.
 */
export function renderSelectNodeHint() {
    return `
    <div class="fs-empty" style="height: 100%; padding: 20px 16px; align-items: flex-start;">
      <div class="fs-empty-icon">\u{1F446}</div>
      <p class="fs-empty-title">Select a node</p>
      <p class="fs-empty-description">Click a step or agent in the graph.</p>

      <div style="width: 100%; margin-top: 12px;">

        <div style="margin-bottom: 12px;">
          <div class="kv-label" style="margin-top: 0;">What is a flow?</div>
          <div class="fs-text-body" style="line-height: 1.5; color: #374151;">
            A pipeline from Signal → Plan → Build → Gate → Deploy → Wisdom.<br/>
            Each flow writes artifacts under
            <code class="mono fs-text-xs">swarm/runs/&lt;run&gt;/</code>
          </div>
        </div>

        <div style="margin-bottom: 12px;">
          <div class="kv-label">What is a step?</div>
          <div class="fs-text-body" style="line-height: 1.5; color: #374151;">
            A stage in the flow executed by one or more agents.<br/>
            Each step reads inputs and writes artifacts.
          </div>
        </div>

        <div style="margin-bottom: 12px;">
          <div class="kv-label">What is an agent?</div>
          <div class="fs-text-body" style="line-height: 1.5; color: #374151;">
            A role with instructions defined in YAML config.<br/>
            Config:
            <code class="mono fs-text-xs">swarm/config/agents/*.yaml</code>
          </div>
        </div>

        <div class="author-only" style="margin-top: 16px; padding: 10px; background: #f0f9ff; border-radius: 6px; border-left: 3px solid #3b82f6;">
          <div class="fs-text-sm" style="font-weight: 600; color: #1e40af; margin-bottom: 6px;">
            First edit
          </div>
          <div class="fs-text-sm" style="color: #374151; line-height: 1.6;">
            1. Select the <strong>build</strong> flow<br/>
            2. Click the <strong>load_context</strong> step<br/>
            3. Follow the <strong>Edit agent</strong> hint
          </div>
          <div class="fs-text-xs fs-text-muted" style="margin-top: 6px;">
            Full guide: <code class="mono" style="font-size: 9px;">docs/FLOW_STUDIO_FIRST_EDIT.md</code>
          </div>
        </div>

        <div class="operator-only" style="margin-top: 16px; padding: 10px; background: #f9fafb; border-radius: 6px;">
          <div class="fs-text-sm fs-text-muted" style="line-height: 1.6;">
            Select a step to see artifact status and run details.
          </div>
        </div>

        <div style="margin-top: 12px; padding-top: 10px; border-top: 1px solid #e5e7eb;">
          <div class="fs-text-xs fs-text-subtle">
            <kbd class="fs-kbd">1-6</kbd> flows
            <kbd class="fs-kbd">/</kbd> search
            <kbd class="fs-kbd">?</kbd> help
          </div>
        </div>

      </div>
    </div>
  `;
}
// ============================================================================
// Error States
// ============================================================================
/**
 * Render an error state for failed run loading.
 */
export function renderRunsLoadError() {
    return `
    <div class="fs-error" style="margin: 8px;">
      <div class="fs-error-icon">\u26A0\uFE0F</div>
      <p class="fs-error-title">Failed to load runs</p>
      <p class="fs-error-description">Check that the Flow Studio server is running.</p>
      <button class="fs-error-action" onclick="location.reload()">Retry</button>
    </div>
  `;
}
/**
 * Render a generic error state with custom title and message.
 */
export function renderErrorState(title, message, actionLabel, actionOnClick) {
    const actionHtml = actionLabel && actionOnClick
        ? `<button class="fs-error-action" onclick="${escapeHtml(actionOnClick)}">${escapeHtml(actionLabel)}</button>`
        : "";
    return `
    <div class="fs-error" style="margin: 8px;">
      <div class="fs-error-icon">\u26A0\uFE0F</div>
      <p class="fs-error-title">${escapeHtml(title)}</p>
      <p class="fs-error-description">${escapeHtml(message)}</p>
      ${actionHtml}
    </div>
  `;
}
// ============================================================================
// Key-Value Display
// ============================================================================
/**
 * Render a single key-value pair.
 */
export function renderKV(label, value, mono = false) {
    const valueClass = mono ? 'class="mono"' : '';
    return `
    <div class="kv-label">${escapeHtml(label)}</div>
    <div ${valueClass}>${escapeHtml(value)}</div>
  `;
}
/**
 * Render a key-value pair with raw HTML value (use with caution).
 */
export function renderKVHtml(label, valueHtml) {
    return `
    <div class="kv-label">${escapeHtml(label)}</div>
    <div>${valueHtml}</div>
  `;
}
// ============================================================================
// Hint Sections
// ============================================================================
/**
 * Render the getting started hint for flow details (author mode).
 */
export function renderGettingStartedHint(flowKey) {
    return `
    <div class="welcome-section" style="margin-bottom: 12px;">
      <div class="fs-text-sm fs-text-muted" style="margin-bottom: 8px;">
        Click a node for details. Press <kbd class="shortcut-key">?</kbd> for shortcuts.
      </div>
      <div class="fs-text-sm fs-text-subtle">
        Artifacts: <code class="mono fs-text-xs">swarm/runs/&lt;run&gt;/${escapeHtml(flowKey || "<flow>")}/</code>
      </div>
    </div>
    <div class="welcome-section">
      <div class="fs-text-sm fs-text-muted" style="margin-bottom: 4px;">Edit flow:</div>
      <pre class="mono fs-text-xs" style="margin: 0;">$EDITOR swarm/config/flows/${escapeHtml(flowKey || "<key>")}.yaml</pre>
    </div>
  `;
}
/**
 * Render the operator mode hint when no timeline is available.
 */
export function renderOperatorFlowHint() {
    return `
    <div class="muted fs-text-sm" style="margin-top: 8px;">
      Select a step for status and artifacts.
    </div>
  `;
}
/**
 * Render a loading placeholder.
 */
export function renderLoading(message = "Loading...") {
    return `<div class="muted">${escapeHtml(message)}</div>`;
}
// ============================================================================
// Tour Menu Items
// ============================================================================
/**
 * Render the "no tour" menu item.
 */
export function renderNoTourMenuItem() {
    return `
    <div class="tour-menu-item" data-tour="">
      <div class="tour-menu-title">No tour</div>
      <div class="tour-menu-desc">Exit current tour</div>
    </div>
  `;
}
/**
 * Render a tour menu item.
 */
export function renderTourMenuItem(tourId, title, description) {
    return `
    <div class="tour-menu-title">${escapeHtml(title)}</div>
    <div class="tour-menu-desc">${escapeHtml(description)}</div>
  `;
}
// ============================================================================
// Agent Usage Item
// ============================================================================
/**
 * Render an agent usage link item.
 */
export function renderAgentUsageItem(flowTitle, stepTitle) {
    return `<span style="color: #3b82f6;">\u2192</span> <strong>${escapeHtml(flowTitle)}</strong> &gt; ${escapeHtml(stepTitle)}`;
}
// ============================================================================
// Step/Agent/Artifact Details Helpers
// ============================================================================
/**
 * Render the step location info (author mode).
 */
export function renderStepLocationInfo(flowKey) {
    return `
    <div class="kv-label">Spec</div>
    <div class="fs-text-sm">
      <span class="mono">swarm/flows/flow-${escapeHtml(flowKey)}.md</span>
    </div>
    <div style="margin-top: 8px;">
      <div class="fs-text-sm fs-text-muted" style="margin-bottom: 4px;">Edit step:</div>
      <pre class="mono fs-text-xs" style="margin: 0;">$EDITOR swarm/config/flows/${escapeHtml(flowKey)}.yaml</pre>
    </div>
  `;
}
/**
 * Render the agent location info (author mode).
 */
export function renderAgentLocationInfo(agentKey) {
    return `
    <div class="kv-label">Files</div>
    <div class="fs-text-sm" style="line-height: 1.8;">
      <span class="mono">swarm/config/agents/${escapeHtml(agentKey)}.yaml</span> <span class="muted">(edit)</span><br/>
      <span class="mono">.claude/agents/${escapeHtml(agentKey)}.md</span> <span class="muted">(generated)</span>
    </div>
    <div style="margin-top: 8px;">
      <div class="fs-text-sm fs-text-muted" style="margin-bottom: 4px;">Edit agent:</div>
      <pre class="mono fs-text-xs" style="margin: 0;">$EDITOR swarm/config/agents/${escapeHtml(agentKey)}.yaml</pre>
    </div>
  `;
}
/**
 * Render agent category hint (operator mode).
 */
export function renderAgentCategoryHint(category, model) {
    return `
    <div class="muted" style="margin-top: 8px;">
      This agent belongs to the <strong>${escapeHtml(category || "unknown")}</strong> role family
      and uses the <strong>${escapeHtml(model || "inherit")}</strong> model.
    </div>
  `;
}
/**
 * Render artifact producer hint (operator mode).
 */
export function renderArtifactProducerHint(stepId, flowKey) {
    return `
    <div class="muted" style="margin-top: 8px;">
      This artifact is produced by the <strong>${escapeHtml(stepId)}</strong> step
      in the <strong>${escapeHtml(flowKey)}</strong> flow.
    </div>
  `;
}
// ============================================================================
// Tabs
// ============================================================================
/**
 * Render tab navigation.
 */
export function renderTabs(tabs) {
    return tabs.map(tab => `<button type="button" role="tab" aria-selected="${tab.active ? "true" : "false"}" class="tab${tab.active ? " active" : ""}" data-tab="${escapeHtml(tab.id)}">${escapeHtml(tab.label)}</button>`).join("");
}
