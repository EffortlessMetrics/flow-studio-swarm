// swarm/tools/flow_studio_ui/src/shortcuts.ts
// Keyboard shortcuts for Flow Studio
//
// This module handles:
// - Global keyboard shortcuts (1-6 for flows, / for search, ? for help)
// - Arrow key navigation between steps
// - Shortcuts help modal

import { state, FLOW_KEYS } from "./state.js";
import { closeSearchDropdown, focusSearch } from "./search.js";
import { createModalFocusManager, type ModalFocusManager } from "./utils.js";
import type { FlowKey, NodeData, ShortcutsCallbacks } from "./domain.js";

// ============================================================================
// Module configuration - callbacks set by consumer
// ============================================================================

let _setActiveFlow: ((flowKey: FlowKey) => Promise<void>) | null = null;
let _showStepDetails: ((nodeData: NodeData) => void) | null = null;
let _toggleSelftestModal: ((show: boolean) => void) | null = null;

/**
 * Configure callbacks for the shortcuts module.
 */
export function configure(callbacks: ShortcutsCallbacks = {}): void {
  if (callbacks.setActiveFlow) _setActiveFlow = callbacks.setActiveFlow;
  if (callbacks.showStepDetails) _showStepDetails = callbacks.showStepDetails;
  if (callbacks.toggleSelftestModal) _toggleSelftestModal = callbacks.toggleSelftestModal;
}

// ============================================================================
// Shortcuts Modal
// ============================================================================

// Focus manager for the shortcuts modal
let shortcutsFocusManager: ModalFocusManager | null = null;

/**
 * Toggle the keyboard shortcuts help modal with focus management.
 */
export function toggleShortcutsModal(show: boolean): void {
  const modal = document.getElementById("shortcuts-modal");
  if (!modal) return;

  // Lazy-init focus manager
  if (!shortcutsFocusManager) {
    shortcutsFocusManager = createModalFocusManager(modal, ".shortcuts-content");
  }

  if (show) {
    modal.classList.add("open");
    shortcutsFocusManager.open(document.activeElement);
  } else {
    modal.classList.remove("open");
    shortcutsFocusManager.close();
  }
}

/**
 * Initialize shortcuts modal close on backdrop click and ESC key.
 */
export function initShortcutsModal(): void {
  const modal = document.getElementById("shortcuts-modal");
  if (!modal) return;

  // Close on backdrop click
  modal.addEventListener("click", (e: MouseEvent) => {
    if (e.target === modal) {
      toggleShortcutsModal(false);
    }
  });

  // Close button click handler
  const closeBtn = document.getElementById("shortcuts-modal-close");
  if (closeBtn) {
    closeBtn.addEventListener("click", () => {
      toggleShortcutsModal(false);
    });
  }

  // Close on ESC key within the modal
  modal.addEventListener("keydown", (e: KeyboardEvent) => {
    if (e.key === "Escape") {
      e.preventDefault();
      e.stopPropagation();
      toggleShortcutsModal(false);
    }
  });
}

// ============================================================================
// Keyboard Shortcuts Handler
// ============================================================================

/**
 * Initialize global keyboard shortcuts.
 */
export function initKeyboardShortcuts(): void {
  document.addEventListener("keydown", (e: KeyboardEvent) => {
    // Don't trigger shortcuts when typing in input
    const activeEl = document.activeElement;
    if (activeEl && (activeEl.tagName === "INPUT" || activeEl.tagName === "TEXTAREA")) {
      return;
    }

    // / - Focus search
    if (e.key === "/") {
      e.preventDefault();
      focusSearch();
    }

    // ? - Show shortcuts modal
    else if (e.key === "?" || (e.shiftKey && e.key === "/")) {
      e.preventDefault();
      toggleShortcutsModal(true);
    }

    // Escape - Close modals/dropdowns
    else if (e.key === "Escape") {
      closeSearchDropdown();
      toggleShortcutsModal(false);
      if (_toggleSelftestModal) _toggleSelftestModal(false);
    }

    // 1-6 - Jump to flows
    else if (e.key >= "1" && e.key <= "6") {
      const flowIndex = parseInt(e.key) - 1;
      if (FLOW_KEYS[flowIndex] && _setActiveFlow) {
        _setActiveFlow(FLOW_KEYS[flowIndex]);
        state.currentStepIndex = -1;
      }
    }

    // Arrow keys - navigate steps
    else if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
      if (!state.currentFlowKey || !state.cy) return;

      const stepNodes = state.cy.nodes('[type = "step"]').sort((a, b) => {
        const orderA = a.data("order") as number;
        const orderB = b.data("order") as number;
        return orderA - orderB;
      });
      if (stepNodes.length === 0) return;

      if (e.key === "ArrowRight") {
        state.currentStepIndex = Math.min(state.currentStepIndex + 1, stepNodes.length - 1);
      } else {
        state.currentStepIndex = Math.max(state.currentStepIndex - 1, 0);
      }

      const targetNode = stepNodes[state.currentStepIndex];
      if (targetNode) {
        state.cy.fit(50);
        targetNode.select();
        if (_showStepDetails) {
          _showStepDetails(targetNode.data() as NodeData);
        }
      }
    }
  });
}
