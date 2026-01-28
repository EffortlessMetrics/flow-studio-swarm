// swarm/tools/flow_studio_ui/src/search.ts
// Search functionality for Flow Studio
//
// This module handles:
// - Search input handling and debouncing
// - Search results rendering
// - Search result selection and navigation

import { state } from "./state.js";
import { Api } from "./api.js";
import { escapeHtml } from "./utils.js";
import type {
  FlowKey,
  SearchResult,
  SearchCallbacks,
  CytoscapeInstance,
} from "./domain.js";

// ============================================================================
// Module configuration - callbacks set by consumer
// ============================================================================

let _setActiveFlow: ((flowKey: FlowKey) => Promise<void>) | null = null;
let _getCy: (() => CytoscapeInstance | null) | null = null;

/**
 * Configure callbacks for the search module.
 * Call this before using other functions to wire up navigation.
 */
export function configure(callbacks: SearchCallbacks = {}): void {
  if (callbacks.setActiveFlow) _setActiveFlow = callbacks.setActiveFlow;
  if (callbacks.getCy) _getCy = callbacks.getCy;
}

/**
 * Get the Cytoscape instance.
 */
function getCy(): CytoscapeInstance | null {
  if (_getCy && typeof _getCy === "function") return _getCy();
  return state.cy;
}

// ============================================================================
// Search Functions
// ============================================================================

/**
 * Perform search query against the API.
 */
export async function performSearch(query: string): Promise<void> {
  if (!query || query.length < 1) {
    closeSearchDropdown();
    return;
  }

  try {
    const data = await Api.search(query);
    state.searchResults = data.results || [];
    renderSearchResults(state.searchResults);
  } catch (err) {
    console.error("Search failed", err);
    closeSearchDropdown();
  }
}

/**
 * Render search results in the dropdown.
 */
export function renderSearchResults(results: SearchResult[]): void {
  const dropdown = document.getElementById("search-dropdown");
  const searchInput = document.getElementById("search-input");
  if (!dropdown) return;

  // Clear existing content safely
  dropdown.innerHTML = "";

  if (!results.length) {
    const noResults = document.createElement("div");
    noResults.className = "search-no-results";
    noResults.textContent = "No results found";
    dropdown.appendChild(noResults);

    dropdown.classList.add("open");
    if (searchInput) {
      searchInput.setAttribute("aria-expanded", "true");
      searchInput.removeAttribute("aria-activedescendant");
    }
    return;
  }

  const fragment = document.createDocumentFragment();

  results.forEach((r, idx) => {
    const typeClass = r.type;
    let label = r.label;
    if (r.type === "step") {
      label = r.flow + " / " + r.label;
    } else if (r.type === "artifact") {
      label = r.flow + " / " + (r.file || r.label);
    }

    const item = document.createElement("div");
    item.className = "search-result";
    if (idx === state.searchSelectedIndex) {
      item.classList.add("selected");
      item.setAttribute("aria-selected", "true");

      // Update aria-activedescendant on input
      if (searchInput) {
        searchInput.setAttribute("aria-activedescendant", `search-result-${idx}`);
      }
    } else {
      item.setAttribute("aria-selected", "false");
    }

    item.setAttribute("role", "option");
    item.setAttribute("data-index", String(idx));
    item.id = `search-result-${idx}`;

    const typeSpan = document.createElement("span");
    typeSpan.className = `search-result-type ${escapeHtml(typeClass)}`;
    typeSpan.textContent = r.type;
    item.appendChild(typeSpan);

    const labelSpan = document.createElement("span");
    labelSpan.className = "search-result-label";
    labelSpan.textContent = label;
    item.appendChild(labelSpan);

    fragment.appendChild(item);
  });

  dropdown.appendChild(fragment);
  dropdown.classList.add("open");

  if (searchInput) {
    searchInput.setAttribute("aria-expanded", "true");
  }

  // Click handlers are managed via event delegation in initSearchHandlers
}

/**
 * Close the search dropdown and reset state.
 */
export function closeSearchDropdown(): void {
  const dropdown = document.getElementById("search-dropdown");
  if (dropdown) {
    dropdown.classList.remove("open");
  }

  const searchInput = document.getElementById("search-input");
  if (searchInput) {
    searchInput.setAttribute("aria-expanded", "false");
    searchInput.removeAttribute("aria-activedescendant");
  }

  state.searchSelectedIndex = -1;
  state.searchResults = [];
}

/**
 * Select a search result by index and navigate to it.
 */
export async function selectSearchResult(index: number): Promise<void> {
  const result = state.searchResults[index];
  if (!result) return;

  closeSearchDropdown();
  const searchInput = document.getElementById("search-input") as HTMLInputElement | null;
  if (searchInput) searchInput.value = "";

  const cy = getCy();

  if (result.type === "flow") {
    if (_setActiveFlow) await _setActiveFlow(result.id as FlowKey);
  } else if (result.type === "step") {
    if (_setActiveFlow && result.flow) {
      await _setActiveFlow(result.flow);
      // Highlight the step node after graph renders
      setTimeout(() => {
        const currentCy = getCy();
        if (currentCy) {
          const nodeId = "step:" + result.flow + ":" + result.id;
          const node = currentCy.getElementById(nodeId);
          if (node) {
            currentCy.fit(50);
            node.select();
          }
        }
      }, 300);
    }
  } else if (result.type === "agent") {
    const targetFlow = result.flows && result.flows[0];
    if (targetFlow && _setActiveFlow) {
      await _setActiveFlow(targetFlow);
      setTimeout(() => {
        const currentCy = getCy();
        if (currentCy) {
          const nodeId = "agent:" + (result.key || result.id);
          const node = currentCy.getElementById(nodeId);
          if (node) {
            currentCy.fit(50);
            node.select();
          }
        }
      }, 300);
    }
  } else if (result.type === "artifact") {
    if (_setActiveFlow && result.flow) await _setActiveFlow(result.flow);
  }
}

/**
 * Initialize search input handlers.
 */
export function initSearchHandlers(): void {
  const searchInput = document.getElementById("search-input") as HTMLInputElement | null;
  const dropdown = document.getElementById("search-dropdown");

  if (!searchInput) return;

  // Initialize ARIA attributes for Combobox pattern
  searchInput.setAttribute("role", "combobox");
  searchInput.setAttribute("aria-autocomplete", "list");
  searchInput.setAttribute("aria-haspopup", "listbox");
  searchInput.setAttribute("aria-expanded", "false");
  searchInput.setAttribute("aria-controls", "search-dropdown");

  searchInput.addEventListener("input", (e: Event) => {
    if (state.searchDebounceTimer) {
      clearTimeout(state.searchDebounceTimer);
    }
    const target = e.target as HTMLInputElement;
    const query = target.value.trim();
    // Optimization: Increased debounce from 200ms to 300ms to reduce API calls while typing
    state.searchDebounceTimer = setTimeout(() => performSearch(query), 300);
  });

  searchInput.addEventListener("keydown", (e: KeyboardEvent) => {
    if (e.key === "Escape") {
      closeSearchDropdown();
      searchInput.blur();
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      if (state.searchResults.length > 0) {
        state.searchSelectedIndex = Math.min(state.searchSelectedIndex + 1, state.searchResults.length - 1);
        renderSearchResults(state.searchResults);
      }
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (state.searchResults.length > 0) {
        state.searchSelectedIndex = Math.max(state.searchSelectedIndex - 1, 0);
        renderSearchResults(state.searchResults);
      }
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (state.searchSelectedIndex >= 0) {
        selectSearchResult(state.searchSelectedIndex);
      } else if (state.searchResults.length > 0) {
        selectSearchResult(0);
      }
    }
  });

  // Close dropdown when clicking outside
  document.addEventListener("click", (e: MouseEvent) => {
    const target = e.target as Node;
    if (!searchInput.contains(target) && dropdown && !dropdown.contains(target)) {
      closeSearchDropdown();
    }
  });

  // Event delegation for search results
  if (dropdown) {
    dropdown.addEventListener("click", (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      const resultItem = target.closest(".search-result");
      if (resultItem) {
        const indexStr = resultItem.getAttribute("data-index");
        if (indexStr) {
          const index = parseInt(indexStr, 10);
          if (!isNaN(index)) {
            selectSearchResult(index);
          }
        }
      }
    });
  }
}

/**
 * Focus the search input.
 */
export function focusSearch(): void {
  const searchInput = document.getElementById("search-input") as HTMLInputElement | null;
  if (searchInput) searchInput.focus();
}
