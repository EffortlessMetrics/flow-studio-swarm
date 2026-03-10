/**
 * Context Budget Settings Module
 *
 * Provides state management and UI for context budget configuration.
 * Follows the same pattern as teaching_mode.ts.
 */
// ============================================================================
// Constants
// ============================================================================
// Storage key for localStorage persistence
const STORAGE_KEY = "flowStudio.contextBudgetOverrides";
// Default values (matching runtime.yaml defaults in v2.4.0)
const DEFAULT_BUDGETS = {
    context_budget_chars: 200000, // ~50k tokens
    history_max_recent_chars: 60000, // ~15k tokens
    history_max_older_chars: 10000, // ~2.5k tokens
    source: "default",
};
// ============================================================================
// Presets
// ============================================================================
/** Preset configurations for common context budget scenarios */
export const PRESETS = {
    lean: {
        id: "lean",
        label: "Lean (25k tokens)",
        description: "Minimal history for fast execution",
        context_budget_chars: 100000,
        history_max_recent_chars: 30000,
        history_max_older_chars: 5000,
    },
    balanced: {
        id: "balanced",
        label: "Balanced (50k tokens)",
        description: "Default balanced settings",
        context_budget_chars: 200000,
        history_max_recent_chars: 60000,
        history_max_older_chars: 10000,
    },
    heavy: {
        id: "heavy",
        label: "Heavy (100k tokens)",
        description: "Maximum context for complex flows",
        context_budget_chars: 400000,
        history_max_recent_chars: 120000,
        history_max_older_chars: 20000,
    },
};
// ============================================================================
// Internal State
// ============================================================================
let _profileOverride = null;
let _effectiveBudgets = { ...DEFAULT_BUDGETS };
let _initialized = false;
/** Registered callbacks */
const _callbacks = [];
// ============================================================================
// localStorage Helpers
// ============================================================================
/**
 * Read profile override from localStorage.
 * Returns null if localStorage is unavailable or key is missing.
 */
function readFromStorage() {
    if (typeof window === "undefined")
        return null;
    try {
        const stored = window.localStorage.getItem(STORAGE_KEY);
        if (stored) {
            return JSON.parse(stored);
        }
    }
    catch (e) {
        console.warn("Failed to read context budget overrides from storage:", e);
    }
    return null;
}
/**
 * Write profile override to localStorage.
 * Silently fails if localStorage is unavailable.
 */
function writeToStorage(override) {
    if (typeof window === "undefined")
        return;
    try {
        if (override) {
            window.localStorage.setItem(STORAGE_KEY, JSON.stringify(override));
        }
        else {
            window.localStorage.removeItem(STORAGE_KEY);
        }
    }
    catch (e) {
        console.warn("Failed to write context budget overrides to storage:", e);
    }
}
// ============================================================================
// Budget Computation
// ============================================================================
/**
 * Apply profile override to defaults to get effective budgets.
 */
function computeEffectiveBudgets(override) {
    if (!override) {
        return { ...DEFAULT_BUDGETS };
    }
    const hasOverrides = override.context_budget_chars !== undefined ||
        override.history_max_recent_chars !== undefined ||
        override.history_max_older_chars !== undefined;
    return {
        context_budget_chars: override.context_budget_chars ?? DEFAULT_BUDGETS.context_budget_chars,
        history_max_recent_chars: override.history_max_recent_chars ?? DEFAULT_BUDGETS.history_max_recent_chars,
        history_max_older_chars: override.history_max_older_chars ?? DEFAULT_BUDGETS.history_max_older_chars,
        source: hasOverrides ? "profile" : "default",
    };
}
/**
 * Notify all registered callbacks of budget changes.
 */
function notifyCallbacks() {
    for (const callback of _callbacks) {
        try {
            callback(_effectiveBudgets);
        }
        catch (e) {
            console.error("Context budget callback error:", e);
        }
    }
}
// ============================================================================
// Preset Detection and Application
// ============================================================================
/**
 * Detect which preset (if any) matches the current effective budgets.
 * Returns null if no preset matches exactly.
 */
export function detectCurrentPreset() {
    const budgets = getContextBudgets();
    for (const presetId of Object.keys(PRESETS)) {
        const preset = PRESETS[presetId];
        if (budgets.context_budget_chars === preset.context_budget_chars &&
            budgets.history_max_recent_chars === preset.history_max_recent_chars &&
            budgets.history_max_older_chars === preset.history_max_older_chars) {
            return presetId;
        }
    }
    return null;
}
/**
 * Apply a preset's values to the current context budgets.
 * @param presetId - The preset to apply ("lean", "balanced", or "heavy")
 */
export async function applyPreset(presetId) {
    const preset = PRESETS[presetId];
    if (!preset) {
        console.warn(`Unknown preset: ${presetId}`);
        return;
    }
    await setContextBudgets({
        context_budget_chars: preset.context_budget_chars,
        history_max_recent_chars: preset.history_max_recent_chars,
        history_max_older_chars: preset.history_max_older_chars,
    });
}
// ============================================================================
// State Management
// ============================================================================
/**
 * Initialize the context budget settings module.
 * Should be called once during app startup.
 */
export function initContextBudgetSettings() {
    if (_initialized)
        return;
    _profileOverride = readFromStorage();
    _effectiveBudgets = computeEffectiveBudgets(_profileOverride);
    _initialized = true;
    // Context budget settings initialized: _effectiveBudgets
}
/**
 * Get the current effective context budgets.
 */
export function getContextBudgets() {
    if (!_initialized) {
        initContextBudgetSettings();
    }
    return { ..._effectiveBudgets };
}
/**
 * Get the current profile override (may be null if using defaults).
 */
export function getProfileOverride() {
    return _profileOverride ? { ..._profileOverride } : null;
}
/**
 * Update profile-level context budget overrides.
 * Pass null to reset to defaults.
 */
export async function setContextBudgets(budgets) {
    if (budgets === null) {
        _profileOverride = null;
    }
    else {
        _profileOverride = {
            ...(_profileOverride ?? {}),
            ...budgets,
        };
    }
    writeToStorage(_profileOverride);
    _effectiveBudgets = computeEffectiveBudgets(_profileOverride);
    notifyCallbacks();
    // TODO: Persist to backend via API call
    // await Api.saveContextBudgets(_profileOverride);
}
/**
 * Reset to default budgets (clear all overrides).
 */
export async function resetToDefaults() {
    await setContextBudgets(null);
}
/**
 * Register a callback to be notified when budgets change.
 * Returns an unsubscribe function.
 */
export function onContextBudgetChange(callback) {
    _callbacks.push(callback);
    // Return unsubscribe function
    return () => {
        const index = _callbacks.indexOf(callback);
        if (index >= 0) {
            _callbacks.splice(index, 1);
        }
    };
}
// ============================================================================
// Modal UI Functions
// ============================================================================
/**
 * Open the context budget settings modal.
 * This should be wired to a button in the header.
 */
export function openContextBudgetModal() {
    const modal = document.getElementById("context-budget-modal");
    if (modal) {
        modal.classList.add("open");
        populateModalForm();
        // Focus first input for accessibility
        const firstInput = modal.querySelector("input");
        if (firstInput) {
            firstInput.focus();
        }
    }
}
/**
 * Close the context budget settings modal.
 */
export function closeContextBudgetModal() {
    const modal = document.getElementById("context-budget-modal");
    if (modal) {
        modal.classList.remove("open");
    }
}
/**
 * Populate the modal form with current values.
 */
function populateModalForm() {
    const budgets = getContextBudgets();
    const totalInput = document.getElementById("budget-total");
    const recentInput = document.getElementById("budget-recent");
    const olderInput = document.getElementById("budget-older");
    if (totalInput)
        totalInput.value = String(budgets.context_budget_chars);
    if (recentInput)
        recentInput.value = String(budgets.history_max_recent_chars);
    if (olderInput)
        olderInput.value = String(budgets.history_max_older_chars);
    // Update source display
    const sourceDisplay = document.querySelector('[data-uiid="flow_studio.modal.context_budget.effective"]');
    if (sourceDisplay) {
        sourceDisplay.innerHTML = `
      <div class="budget-value"><strong>Total Budget:</strong> ${budgets.context_budget_chars.toLocaleString()} chars (~${Math.round(budgets.context_budget_chars / 4000)}k tokens)</div>
      <div class="budget-value"><strong>Recent Step:</strong> ${budgets.history_max_recent_chars.toLocaleString()} chars (~${Math.round(budgets.history_max_recent_chars / 4000)}k tokens)</div>
      <div class="budget-value"><strong>Older Steps:</strong> ${budgets.history_max_older_chars.toLocaleString()} chars (~${Math.round(budgets.history_max_older_chars / 4000)}k tokens)</div>
      <div class="budget-source">Source: <code>${budgets.source}</code></div>
    `;
    }
    // Update preset button active states
    updatePresetButtonStates();
}
/**
 * Read values from the modal form.
 */
function readModalForm() {
    const totalInput = document.getElementById("budget-total");
    const recentInput = document.getElementById("budget-recent");
    const olderInput = document.getElementById("budget-older");
    return {
        context_budget_chars: totalInput ? parseInt(totalInput.value, 10) : undefined,
        history_max_recent_chars: recentInput ? parseInt(recentInput.value, 10) : undefined,
        history_max_older_chars: olderInput ? parseInt(olderInput.value, 10) : undefined,
    };
}
/**
 * Update the active state of preset buttons based on current settings.
 * Toggles the `.active` class on preset buttons based on whether the current
 * budget settings match that preset.
 */
export function updatePresetButtonStates() {
    const currentPreset = detectCurrentPreset();
    const presetButtons = document.querySelectorAll(".btn-preset[data-preset]");
    presetButtons.forEach((btn) => {
        const presetId = btn.dataset.preset;
        if (presetId === currentPreset) {
            btn.classList.add("active");
            btn.setAttribute("aria-pressed", "true");
        }
        else {
            btn.classList.remove("active");
            btn.setAttribute("aria-pressed", "false");
        }
    });
}
// ============================================================================
// Event Handler Initialization
// ============================================================================
/**
 * Initialize modal event handlers.
 * Should be called after DOM is ready.
 */
export function initContextBudgetModalHandlers() {
    // Close button
    const closeBtn = document.querySelector('[data-uiid="flow_studio.modal.context_budget.close"]');
    if (closeBtn) {
        closeBtn.addEventListener("click", closeContextBudgetModal);
    }
    // Save button
    const saveBtn = document.querySelector('[data-uiid="flow_studio.modal.context_budget.save"]');
    if (saveBtn) {
        saveBtn.addEventListener("click", async () => {
            const values = readModalForm();
            await setContextBudgets(values);
            closeContextBudgetModal();
        });
    }
    // Reset button
    const resetBtn = document.querySelector('[data-uiid="flow_studio.modal.context_budget.reset"]');
    if (resetBtn) {
        resetBtn.addEventListener("click", async () => {
            await resetToDefaults();
            populateModalForm();
        });
    }
    // Backdrop click to close
    const modal = document.getElementById("context-budget-modal");
    if (modal) {
        modal.addEventListener("click", (e) => {
            if (e.target === modal) {
                closeContextBudgetModal();
            }
        });
    }
    // Header trigger button
    const triggerBtn = document.querySelector('[data-uiid="flow_studio.header.context_budget.trigger"]');
    if (triggerBtn) {
        triggerBtn.addEventListener("click", openContextBudgetModal);
    }
    // Escape key to close
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && modal?.classList.contains("open")) {
            closeContextBudgetModal();
        }
    });
    // Preset buttons - listen for clicks on .btn-preset[data-preset] elements
    const presetButtons = document.querySelectorAll(".btn-preset[data-preset]");
    presetButtons.forEach((btn) => {
        btn.addEventListener("click", async () => {
            const presetId = btn.dataset.preset;
            if (presetId && PRESETS[presetId]) {
                await applyPreset(presetId);
                populateModalForm();
            }
        });
    });
}
