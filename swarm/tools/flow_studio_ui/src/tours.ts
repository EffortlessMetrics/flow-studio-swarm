// swarm/tools/flow_studio_ui/src/tours.ts
// Tour system for Flow Studio
//
// This module handles:
// - Loading and displaying available tours
// - Tour navigation (prev/next/exit)
// - Flow and step highlighting during tours

import { state } from "./state.js";
import { Api } from "./api.js";
import type { FlowKey, Tour, TourStep, ToursCallbacks } from "./domain.js";

// ============================================================================
// Tour State
// ============================================================================

let currentTour: Tour | null = null;
let currentTourStep = 0;
let availableTours: Tour[] = [];

// ============================================================================
// Module configuration - callbacks set by consumer
// ============================================================================

let _setActiveFlow: ((flowKey: FlowKey) => Promise<void>) | null = null;

/**
 * Configure callbacks for the tours module.
 */
export function configure(callbacks: ToursCallbacks = {}): void {
  if (callbacks.setActiveFlow) _setActiveFlow = callbacks.setActiveFlow;
}

// ============================================================================
// Tour Loading
// ============================================================================

/**
 * Load available tours from API.
 */
export async function loadTours(): Promise<void> {
  try {
    const data = await Api.getTours();
    availableTours = data.tours || [];
    renderTourMenu();
  } catch (err) {
    console.error("Failed to load tours", err);
    availableTours = [];
  }
}

/**
 * Render the tour dropdown menu.
 */
export function renderTourMenu(): void {
  const menu = document.getElementById("tour-menu");
  if (!menu) return;

  menu.innerHTML = `
    <div class="tour-menu-item" data-tour="">
      <div class="tour-menu-title">No tour</div>
      <div class="tour-menu-desc">Exit current tour</div>
    </div>
  `;

  availableTours.forEach(tour => {
    const item = document.createElement("button");
    item.className = "tour-menu-item";
    item.dataset.tour = tour.id;
    item.innerHTML = `
      <div class="tour-menu-title">${tour.title}</div>
      <div class="tour-menu-desc">${tour.description || ""}</div>
    `;
    menu.appendChild(item);
  });

  // Add click handlers
  menu.querySelectorAll(".tour-menu-item").forEach(item => {
    item.addEventListener("click", () => {
      const tourId = (item as HTMLElement).dataset.tour;
      if (tourId) {
        startTour(tourId);
      } else {
        exitTour();
      }
      closeMenu();
    });
  });
}

// ============================================================================
// Tour Navigation
// ============================================================================

/**
 * Start a tour by ID.
 */
export async function startTour(tourId: string): Promise<void> {
  try {
    const data = await Api.getTourById(tourId);
    currentTour = data;
    currentTourStep = 0;
    showTourStep();
    updateTourButton(true);
  } catch (err) {
    console.error("Failed to start tour", err);
  }
}

/**
 * Exit the current tour.
 */
export function exitTour(): void {
  currentTour = null;
  currentTourStep = 0;
  hideTourCard();
  clearTourHighlight();
  updateTourButton(false);
}

/**
 * Show the current tour step.
 */
export function showTourStep(): void {
  if (!currentTour || !currentTour.steps || currentTourStep >= currentTour.steps.length) {
    exitTour();
    return;
  }

  const step = currentTour.steps[currentTourStep];
  const total = currentTour.steps.length;

  // Update card content
  const stepNumber = document.getElementById("tour-step-number");
  const cardTitle = document.getElementById("tour-card-title");
  const cardText = document.getElementById("tour-card-text");

  if (stepNumber) stepNumber.textContent = `Step ${currentTourStep + 1} of ${total}`;
  if (cardTitle) cardTitle.textContent = step.title;
  if (cardText) cardText.textContent = step.text;

  // Update navigation buttons
  const prevBtn = document.getElementById("tour-prev-btn") as HTMLButtonElement | null;
  const nextBtn = document.getElementById("tour-next-btn");
  if (prevBtn) prevBtn.disabled = currentTourStep === 0;
  if (nextBtn) nextBtn.textContent = currentTourStep === total - 1 ? "Finish" : "Next \u2192";

  // Show tour card
  const tourCard = document.getElementById("tour-card");
  if (tourCard) tourCard.style.display = "block";

  // Execute the tour action (select flow or step)
  executeTourAction(step);
}

/**
 * Execute tour action (navigate to flow/step).
 */
async function executeTourAction(step: TourStep): Promise<void> {
  const target = step.target;

  if (target.type === "flow") {
    // Select the flow
    if (_setActiveFlow) await _setActiveFlow(target.flow);
    highlightFlow(target.flow);
  } else if (target.type === "step") {
    // First select the flow, then highlight the step
    if (_setActiveFlow) await _setActiveFlow(target.flow);
    if (target.step) {
      highlightStep(target.flow, target.step);
    }
  }
}

/**
 * Go to next tour step.
 */
export function nextTourStep(): void {
  if (currentTour && currentTourStep < currentTour.steps.length - 1) {
    currentTourStep++;
    showTourStep();
  } else {
    exitTour();
  }
}

/**
 * Go to previous tour step.
 */
export function prevTourStep(): void {
  if (currentTourStep > 0) {
    currentTourStep--;
    showTourStep();
  }
}

// ============================================================================
// Highlighting
// ============================================================================

/**
 * Highlight a flow in the sidebar and SDLC bar.
 */
export function highlightFlow(flowKey: FlowKey): void {
  clearTourHighlight();

  // Highlight in sidebar
  const flowItem = document.querySelector(`.flow-item[data-key="${flowKey}"]`);
  if (flowItem) {
    flowItem.classList.add("tour-highlight");
  }

  // Highlight in SDLC bar
  const sdlcItem = document.querySelector(`.sdlc-flow[data-key="${flowKey}"]`);
  if (sdlcItem) {
    sdlcItem.classList.add("tour-highlight");
  }
}

/**
 * Highlight a step in the graph.
 */
export function highlightStep(flowKey: FlowKey, stepId: string): void {
  clearTourHighlight();

  if (state.cy) {
    // Dim all nodes first
    state.cy.nodes().forEach(node => {
      // Use class manipulation through the element
      (node as unknown as { addClass(cls: string): void }).addClass("tour-dimmed");
    });

    // Highlight the target step
    const nodeId = `step:${flowKey}:${stepId}`;
    const node = state.cy.getElementById(nodeId);
    if (node) {
      (node as unknown as { removeClass(cls: string): void }).removeClass("tour-dimmed");
      (node as unknown as { addClass(cls: string): void }).addClass("tour-highlight");

      // Also highlight connected agents
      const connectedEdges = (node as unknown as { connectedEdges(): { connectedNodes(): { forEach(fn: (n: unknown) => void): void } } }).connectedEdges();
      connectedEdges.connectedNodes().forEach((n: unknown) => {
        (n as { removeClass(cls: string): void }).removeClass("tour-dimmed");
      });

      // Center on the node
      state.cy.center();
    }
  }
}

/**
 * Clear all tour highlights.
 */
export function clearTourHighlight(): void {
  // Clear sidebar highlights
  document.querySelectorAll(".tour-highlight").forEach(el => {
    el.classList.remove("tour-highlight");
  });

  // Clear graph highlights
  if (state.cy) {
    state.cy.nodes().forEach(node => {
      (node as unknown as { removeClass(cls: string): void }).removeClass("tour-highlight");
      (node as unknown as { removeClass(cls: string): void }).removeClass("tour-dimmed");
    });
  }
}

// ============================================================================
// UI Updates
// ============================================================================

/**
 * Hide the tour card.
 */
export function hideTourCard(): void {
  const card = document.getElementById("tour-card");
  if (card) {
    card.style.display = "none";
  }
}

/**
 * Update tour button appearance.
 */
export function updateTourButton(active: boolean): void {
  const btn = document.getElementById("tour-btn");
  if (btn) {
    btn.classList.toggle("active", active);
    const label = btn.querySelector("span:first-child");
    if (label) {
      label.textContent = active && currentTour ? currentTour.title : "Tour";
    }
  }
}

/**
 * Toggle tour dropdown menu visibility.
 */
export function toggleTourMenu(): void {
  const menu = document.getElementById("tour-menu");
  const btn = document.getElementById("tour-btn");
  if (menu) {
    const isOpen = menu.classList.toggle("open");
    // Keep aria-expanded in sync with menu state
    if (btn) {
      btn.setAttribute("aria-expanded", isOpen ? "true" : "false");
    }
  }
}

/**
 * Close tour dropdown menu.
 */
export function closeMenu(): void {
  const menu = document.getElementById("tour-menu");
  const btn = document.getElementById("tour-btn");
  if (menu) {
    menu.classList.remove("open");
    // Keep aria-expanded in sync with menu state
    if (btn) {
      btn.setAttribute("aria-expanded", "false");
    }
  }
}

// ============================================================================
// Event Handlers
// ============================================================================

/**
 * Initialize tour event handlers.
 */
export function initTourHandlers(): void {
  // Dropdown toggle
  const tourBtn = document.getElementById("tour-btn");
  if (tourBtn) {
    tourBtn.addEventListener("click", (e: MouseEvent) => {
      e.stopPropagation();
      toggleTourMenu();
    });
  }

  // Close menu when clicking outside
  document.addEventListener("click", (e: MouseEvent) => {
    const dropdown = document.getElementById("tour-dropdown");
    const target = e.target as Node;
    if (dropdown && !dropdown.contains(target)) {
      closeMenu();
    }
  });

  // Tour navigation buttons
  const prevBtn = document.getElementById("tour-prev-btn");
  const nextBtn = document.getElementById("tour-next-btn");
  const exitBtn = document.getElementById("tour-exit-btn");

  if (prevBtn) {
    prevBtn.addEventListener("click", prevTourStep);
  }

  if (nextBtn) {
    nextBtn.addEventListener("click", nextTourStep);
  }

  if (exitBtn) {
    exitBtn.addEventListener("click", exitTour);
  }
}

/**
 * Get the current tour ID if one is active.
 */
export function getCurrentTourId(): string | null {
  return currentTour?.id || null;
}
