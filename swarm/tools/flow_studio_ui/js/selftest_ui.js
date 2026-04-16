// swarm/tools/flow_studio_ui/src/selftest_ui.ts
// Selftest modal UI for Flow Studio
//
// This module handles:
// - Selftest plan caching and loading
// - Selftest modal rendering and interactions
// - Individual step detail modals
// - Copy-to-clipboard helpers
import { state } from "./state.js";
import { Api } from "./api.js";
import { escapeHtml, copyToClipboard, createModalFocusManager } from "./utils.js";
// ============================================================================
// Selftest Plan Caching
// ============================================================================
/**
 * Fetch and cache selftest plan.
 */
export async function getSelftestPlan() {
    if (state.selftestPlanCache)
        return state.selftestPlanCache;
    try {
        const plan = await Api.getSelftestPlan();
        state.selftestPlanCache = plan;
        return plan;
    }
    catch (err) {
        console.error("Failed to load selftest plan", err);
        return null;
    }
}
// ============================================================================
// Modal Visibility
// ============================================================================
// Focus manager for the selftest modal
let selftestFocusManager = null;
/**
 * Toggle selftest modal visibility with focus management.
 */
export function toggleSelftestModal(show) {
    const modal = document.getElementById("selftest-modal");
    if (!modal)
        return;
    // Lazy-init focus manager
    if (!selftestFocusManager) {
        selftestFocusManager = createModalFocusManager(modal, ".selftest-step-content");
    }
    if (show) {
        modal.classList.add("open");
        selftestFocusManager.open(document.activeElement);
    }
    else {
        modal.classList.remove("open");
        selftestFocusManager.close();
    }
}
/**
 * Initialize selftest modal close on backdrop click and keyboard handling.
 */
export function initSelftestModal() {
    const modal = document.getElementById("selftest-modal");
    if (!modal)
        return;
    modal.addEventListener("click", (e) => {
        if (e.target === modal) {
            toggleSelftestModal(false);
        }
    });
    modal.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            e.preventDefault();
            toggleSelftestModal(false);
        }
    });
}
// ============================================================================
// Copy Helpers
// ============================================================================
/**
 * Show copy success feedback with toast.
 */
export function showCopyFeedback(message) {
    const feedback = document.createElement("div");
    feedback.style.cssText = `
    position: fixed;
    bottom: 20px;
    right: 20px;
    background: #10b981;
    color: white;
    padding: 12px 16px;
    border-radius: 6px;
    font-size: 14px;
    z-index: 3000;
    opacity: 0;
    animation: fadeInOut 2s ease-in-out;
  `;
    feedback.textContent = message;
    document.body.appendChild(feedback);
    setTimeout(() => feedback.remove(), 2000);
}
/**
 * Show copy fallback box (for clipboard API unavailable).
 */
export function showCopyFallback(text, message) {
    const box = document.createElement("div");
    box.style.cssText = `
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    background: white;
    padding: 20px;
    border-radius: 8px;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
    z-index: 3001;
    max-width: 500px;
    text-align: center;
  `;
    box.innerHTML = `
    <p style="margin: 0 0 12px 0; color: #374151; font-size: 14px;">${escapeHtml(message)}</p>
    <div style="background: #f3f4f6; padding: 12px; border-radius: 4px; margin-bottom: 12px; text-align: left; overflow-x: auto;">
      <code class="fs-text-body" style="font-family: monospace; color: #111827;">${escapeHtml(text)}</code>
    </div>
    <p class="fs-text-body fs-text-muted" style="margin: 0 0 8px 0;">Use Ctrl+C to copy</p>
    <button class="fs-text-body" onclick="this.parentElement.parentElement.remove()" style="padding: 8px 16px; background: #3b82f6; color: white; border: none; border-radius: 4px; cursor: pointer;">Close</button>
  `;
    document.body.appendChild(box);
}
/**
 * Copy command and show instructions.
 */
export function copyAndRun(cmd) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(cmd).then(() => {
            showCopyFeedback(`Copied! Run in terminal: ${cmd}`);
        }).catch(() => {
            showCopyFallback(cmd, "Copy this command and run it in your terminal:");
        });
    }
    else {
        showCopyFallback(cmd, "Copy this command and run it in your terminal:");
    }
}
// ============================================================================
// Selftest Step Modal
// ============================================================================
/**
 * Show selftest step details in modal.
 */
export async function showSelftestStepModal(stepId) {
    const plan = await getSelftestPlan();
    if (!plan) {
        renderSelftestPlanError("Selftest plan not available", "Run this command to generate the plan:\n\nuv run swarm/tools/selftest.py --plan --json");
        toggleSelftestModal(true);
        return;
    }
    const step = plan.steps.find(s => s.id === stepId);
    if (!step) {
        renderSelftestPlanError("Step not found", `Step "${stepId}" is not available in the selftest plan.`);
        toggleSelftestModal(true);
        return;
    }
    renderSelftestStepModal(step);
    toggleSelftestModal(true);
}
/**
 * Render error state in selftest modal.
 */
export function renderSelftestPlanError(title, message) {
    const body = document.getElementById("selftest-modal-body");
    if (!body)
        return;
    body.innerHTML = `
    <div style="padding: 24px; text-align: center;">
      <div style="font-size: 32px; margin-bottom: 12px;">\u26a0\ufe0f</div>
      <h3 style="margin: 0 0 12px 0; font-size: 16px; color: #dc2626;">${escapeHtml(title)}</h3>
      <p class="fs-text-muted" style="margin: 0 0 16px 0; font-size: 13px; line-height: 1.6;">${escapeHtml(message)}</p>
      <div style="background: #fef2f2; padding: 12px; border-left: 3px solid #dc2626; border-radius: 4px; margin: 12px 0; text-align: left;">
        <code class="fs-mono-sm" style="display: block; padding: 8px; white-space: pre-wrap; word-break: break-all; color: #7f1d1d;">uv run swarm/tools/selftest.py --plan --json</code>
      </div>
    </div>
  `;
}
/**
 * Render the selftest step explanation modal.
 */
export function renderSelftestStepModal(step) {
    const body = document.getElementById("selftest-modal-body");
    if (!body)
        return;
    const tierClass = (step.tier || "optional").toLowerCase();
    const tierLabel = (step.tier || "optional").toUpperCase();
    // Tier tooltip descriptions
    const tierTooltips = {
        kernel: "Core repository health - blocking if failed",
        governance: "Swarm contracts - can be degraded but should be reviewed",
        optional: "Code quality checks - informational only"
    };
    const tierTooltip = tierTooltips[tierClass] || tierTooltips.optional;
    let depsHtml = "";
    if (step.depends_on && step.depends_on.length > 0) {
        depsHtml = `
      <div class="selftest-dependencies">
        <div class="selftest-dependencies-title">\u23f3 Depends on:</div>
        <div class="selftest-dependencies-list">
          ${step.depends_on.map(dep => `<div class="selftest-dep-badge">${escapeHtml(dep)}</div>`).join("")}
        </div>
      </div>
    `;
    }
    let acHtml = "";
    if (step.ac_ids && step.ac_ids.length > 0) {
        const tierColorClassMap = {
            kernel: "critical",
            governance: "warning",
            optional: "pass"
        };
        const tierColorClass = tierColorClassMap[tierClass] || "pass";
        acHtml = `
      <div class="selftest-ac-container">
        <span class="selftest-ac-label">\ud83d\udccb Acceptance Criteria</span>
        <div class="selftest-ac-badges">
          ${step.ac_ids.map(ac => `<div class="selftest-ac-badge ${tierColorClass}" title="${escapeHtml(ac)} (Tier: ${step.tier || 'OPTIONAL'})">${escapeHtml(ac)}</div>`).join("")}
        </div>
      </div>
    `;
    }
    const commands = [
        `uv run swarm/tools/selftest.py --step ${step.id}`,
        `uv run swarm/tools/selftest.py --plan | grep -A 5 "${step.id}"`
    ];
    const commandsHtml = `
    <div class="selftest-commands">
      <div class="selftest-commands-title">\ud83d\udcbb Run this step:</div>
      ${commands.map(cmd => `
        <div class="selftest-command">
          <span class="fs-text-xs" style="flex: 1;">${escapeHtml(cmd)}</span>
          <button class="selftest-command-copy-btn" onclick="window.copyToClipboard && window.copyToClipboard('${escapeHtml(cmd).replace(/'/g, "\\'")}')" title="Copy" aria-label="Copy command to clipboard">\ud83d\udccb</button>
        </div>
      `).join("")}
    </div>
  `;
    const failedSteps = state.governanceStatus?.governance?.selftest?.failed_steps || [];
    const degradedSteps = state.governanceStatus?.governance?.selftest?.degraded_steps || [];
    const isFailed = failedSteps.includes(step.id);
    const isDegraded = degradedSteps.includes(step.id);
    let statusBadge = '';
    if (isFailed) {
        statusBadge = '<div class="fs-text-xs" style="padding: 3px 8px; background: #fee2e2; color: #991b1b; border-radius: 3px; font-weight: 600;" title="This step failed. Issues must be resolved before merging.">\u274c FAILED</div>';
    }
    else if (isDegraded) {
        statusBadge = '<div class="fs-text-xs" style="padding: 3px 8px; background: #fef3c7; color: #92400e; border-radius: 3px; font-weight: 600;" title="This step has non-blocking issues. Work can proceed but review recommended.">\u26a0\ufe0f DEGRADED</div>';
    }
    else {
        statusBadge = '<div class="fs-text-xs" style="padding: 3px 8px; background: #dcfce7; color: #14532d; border-radius: 3px; font-weight: 600;" title="This step passed all checks.">\u2705 PASS</div>';
    }
    body.innerHTML = `
    <div class="selftest-step-header" style="flex-wrap: wrap;">
      <div class="selftest-step-id">${escapeHtml(step.id)}</div>
      <div class="selftest-step-tier-badge ${tierClass}" title="${tierTooltip}">${tierLabel}</div>
      ${statusBadge}
    </div>

    <h3 class="selftest-step-title">${escapeHtml(step.description || step.id)}</h3>

    <div class="selftest-step-metadata">
      <div class="selftest-metadata-row">
        <div class="selftest-metadata-label">Tier</div>
        <div class="selftest-metadata-value">${tierLabel}</div>
      </div>
      <div class="selftest-metadata-row">
        <div class="selftest-metadata-label">Category</div>
        <div class="selftest-metadata-value">${escapeHtml(step.category || "\u2014")}</div>
      </div>
      <div class="selftest-metadata-row">
        <div class="selftest-metadata-label">Severity</div>
        <div class="selftest-metadata-value">${escapeHtml(step.severity || "\u2014")}</div>
      </div>
    </div>

    ${acHtml}
    ${depsHtml}
    ${commandsHtml}

    <div class="fs-text-body fs-text-muted" style="margin-top: 16px; padding-top: 12px; border-top: 1px solid #e5e7eb;">
      <strong>Learn more:</strong> See <code style="background: #f3f4f6; padding: 2px 4px; border-radius: 3px;">docs/SELFTEST_SYSTEM.md</code> for detailed information.
    </div>
  `;
}
// ============================================================================
// Selftest Tab Rendering
// ============================================================================
/**
 * Render selftest plan in a tab container.
 */
export async function renderSelftestTab(container) {
    const plan = await getSelftestPlan();
    if (!plan) {
        container.innerHTML = '<div class="muted" style="padding: 8px;">Failed to load selftest plan. Try running: <code>make selftest --plan</code></div>';
        return;
    }
    const summary = plan.summary || { total: 0, by_tier: { kernel: 0, governance: 0, optional: 0 } };
    const html = `
    <div class="kv-label">Selftest Summary</div>
    <div class="fs-text-body" style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px;">
      <div>
        <div class="muted fs-text-sm" style="margin-bottom: 2px;">Total Steps</div>
        <div style="font-size: 14px; font-weight: 600;">${summary.total || 0}</div>
      </div>
      <div>
        <div class="muted fs-text-sm" style="margin-bottom: 2px;">Kernel Steps</div>
        <div style="font-size: 14px; font-weight: 600;">${summary.by_tier?.kernel || 0}</div>
      </div>
    </div>

    <div class="kv-label">View Selftest Plan</div>
    <button class="fs-text-body" onclick="window.showSelftestPlanModal && window.showSelftestPlanModal()" style="padding: 6px 12px; background: #3b82f6; color: white; border: none; border-radius: 4px; cursor: pointer; margin-bottom: 12px;">
      \ud83d\udccb View Full Plan
    </button>

    <div class="kv-label">Quick Commands</div>
    <div style="display: flex; flex-direction: column; gap: 6px;">
      <button class="fs-mono-sm" onclick="window.copyAndRun && window.copyAndRun('uv run swarm/tools/selftest.py --plan')" style="padding: 6px 10px; text-align: left; background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 4px; cursor: pointer;">
        Show plan
      </button>
      <button class="fs-mono-sm" onclick="window.copyAndRun && window.copyAndRun('uv run swarm/tools/selftest.py')" style="padding: 6px 10px; text-align: left; background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 4px; cursor: pointer;">
        Run selftest
      </button>
    </div>
  `;
    container.innerHTML = html;
}
// ============================================================================
// Full Selftest Plan Modal
// ============================================================================
/**
 * Show full selftest plan in modal.
 */
export async function showSelftestPlanModal() {
    const plan = await getSelftestPlan();
    if (!plan) {
        alert("Failed to load selftest plan");
        return;
    }
    const body = document.getElementById("selftest-modal-body");
    if (!body)
        return;
    const tierColors = { kernel: '#dc2626', governance: '#f59e0b', optional: '#3b82f6' };
    // Tier tooltip descriptions for the plan list
    const tierTooltips = {
        kernel: "Core repository health - blocking if failed",
        governance: "Swarm contracts - can be degraded but should be reviewed",
        optional: "Code quality checks - informational only"
    };
    const html = `
    <h3 style="margin: 0 0 16px 0; font-size: 16px; font-weight: 600;">Selftest Plan</h3>
    <div class="fs-text-sm fs-text-muted" style="margin-bottom: 12px;">
      Total: <strong>${plan.summary?.total || 0}</strong> |
      Kernel: <strong>${plan.summary?.by_tier?.kernel || 0}</strong> |
      Governance: <strong>${plan.summary?.by_tier?.governance || 0}</strong> |
      Optional: <strong>${plan.summary?.by_tier?.optional || 0}</strong>
    </div>

    <div class="fs-text-sm" style="margin: 12px 0; padding: 12px; background: #f9fafb; border-radius: 6px;">
      <div style="font-weight: 600; margin-bottom: 8px;">How to read selftest results</div>
      <div style="display: grid; grid-template-columns: auto 1fr; gap: 8px;">
        <span title="This step passed all checks.">PASS</span><span>All checks passed</span>
        <span title="This step has non-blocking issues. Work can proceed but review recommended.">DEGRADED</span><span>Non-blocking issues - proceed with caution</span>
        <span title="This step failed. Issues must be resolved before merging.">FAIL</span><span>Blocking failures - must be resolved</span>
      </div>
      <div class="fs-text-muted" style="margin-top: 8px;">
        Tiers: <strong title="Core repository health - blocking if failed">KERNEL</strong> (blocking) &rarr; <strong title="Swarm contracts - can be degraded but should be reviewed">GOVERNANCE</strong> (important) &rarr; <strong title="Code quality checks - informational only">OPTIONAL</strong> (informational)
      </div>
    </div>

    <div class="selftest-plan-list">
      ${(plan.steps || []).map(step => {
        const tierClass = (step.tier || 'optional').toLowerCase();
        const tierLabel = (step.tier || 'OPTIONAL').toUpperCase();
        const tierColor = tierColors[tierClass] || '#6b7280';
        const tierTooltip = tierTooltips[tierClass] || tierTooltips.optional;
        const failedSteps = state.governanceStatus?.governance?.selftest?.failed_steps || [];
        const degradedSteps = state.governanceStatus?.governance?.selftest?.degraded_steps || [];
        const isFailed = failedSteps.includes(step.id);
        const isDegraded = degradedSteps.includes(step.id);
        const statusIcon = isFailed ? '\u274c' : isDegraded ? '\u26a0\ufe0f' : '\u2705';
        const statusText = isFailed ? 'FAIL' : isDegraded ? 'DEGRADED' : 'PASS';
        const statusTooltip = isFailed
            ? 'This step failed. Issues must be resolved before merging.'
            : isDegraded
                ? 'This step has non-blocking issues. Work can proceed but review recommended.'
                : 'This step passed all checks.';
        return `
          <div class="selftest-plan-item ${tierClass}" onclick="window.showSelftestStepModal && window.showSelftestStepModal('${escapeHtml(step.id)}')" style="${isFailed ? 'background: #fee;' : isDegraded ? 'background: #fff3cd;' : ''}">
            <div class="selftest-plan-item-row">
              <div style="display: flex; align-items: center; gap: 8px; flex: 1;">
                <span style="font-size: 14px;" title="${statusTooltip}">${statusIcon}</span>
                <div style="flex: 1;">
                  <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 2px;">
                    <span class="selftest-plan-item-id">${escapeHtml(step.id)}</span>
                    <span class="selftest-step-tier-badge ${tierClass}" style="font-size: 8px; padding: 2px 4px;" title="${tierTooltip}">${tierLabel}</span>
                    <span style="font-size: 9px; color: #6b7280;" title="${statusTooltip}">${statusText}</span>
                  </div>
                  <div class="selftest-plan-item-desc fs-text-sm" style="color: #374151;">${escapeHtml(step.description || '')}</div>
                </div>
              </div>
              <div class="selftest-plan-item-icon">\u2192</div>
            </div>
          </div>
        `;
    }).join("")}
    </div>
  `;
    body.innerHTML = html;
    toggleSelftestModal(true);
}
// ============================================================================
// Window Exports (for onclick handlers in HTML)
// ============================================================================
if (typeof window !== "undefined") {
    window.copyAndRun = copyAndRun;
    window.showSelftestPlanModal = showSelftestPlanModal;
    window.showSelftestStepModal = showSelftestStepModal;
    window.toggleSelftestModal = toggleSelftestModal;
}
