// swarm/tools/flow_studio_ui/src/search.ts
// Search functionality for Flow Studio
//
// This module handles:
// - Search input handling and debouncing
// - Search results rendering
// - Search result selection and navigation
import { state } from "./state.js";
import { Api } from "./api.js";
// ============================================================================
// Module configuration - callbacks set by consumer
// ============================================================================
let _setActiveFlow = null;
let _getCy = null;
/**
 * Configure callbacks for the search module.
 * Call this before using other functions to wire up navigation.
 */
export function configure(callbacks = {}) {
    if (callbacks.setActiveFlow)
        _setActiveFlow = callbacks.setActiveFlow;
    if (callbacks.getCy)
        _getCy = callbacks.getCy;
}
/**
 * Get the Cytoscape instance.
 */
function getCy() {
    if (_getCy && typeof _getCy === "function")
        return _getCy();
    return state.cy;
}
// ============================================================================
// Search Functions
// ============================================================================
/**
 * Perform search query against the API.
 */
export async function performSearch(query) {
    if (!query || query.length < 1) {
        closeSearchDropdown();
        return;
    }
    try {
        const data = await Api.search(query);
        state.searchResults = data.results || [];
        renderSearchResults(state.searchResults);
    }
    catch (err) {
        console.error("Search failed", err);
        closeSearchDropdown();
    }
}
/**
 * Render search results in the dropdown.
 */
export function renderSearchResults(results) {
    const dropdown = document.getElementById("search-dropdown");
    if (!dropdown)
        return;
    if (!results.length) {
        dropdown.innerHTML = '<div class="search-no-results">No results found</div>';
        dropdown.classList.add("open");
        return;
    }
    dropdown.innerHTML = results.map((r, idx) => {
        const typeClass = r.type;
        let label = r.label;
        if (r.type === "step") {
            label = r.flow + " / " + r.label;
        }
        else if (r.type === "artifact") {
            label = r.flow + " / " + (r.file || r.label);
        }
        return '<div class="search-result' + (idx === state.searchSelectedIndex ? ' selected' : '') + '" data-index="' + idx + '">' +
            '<span class="search-result-type ' + typeClass + '">' + r.type + '</span>' +
            '<span class="search-result-label">' + label + '</span>' +
            '</div>';
    }).join("");
    dropdown.classList.add("open");
    // Click handlers are managed via event delegation in initSearchHandlers
}
/**
 * Close the search dropdown and reset state.
 */
export function closeSearchDropdown() {
    const dropdown = document.getElementById("search-dropdown");
    if (dropdown) {
        dropdown.classList.remove("open");
    }
    state.searchSelectedIndex = -1;
    state.searchResults = [];
}
/**
 * Select a search result by index and navigate to it.
 */
export async function selectSearchResult(index) {
    const result = state.searchResults[index];
    if (!result)
        return;
    closeSearchDropdown();
    const searchInput = document.getElementById("search-input");
    if (searchInput)
        searchInput.value = "";
    const cy = getCy();
    if (result.type === "flow") {
        if (_setActiveFlow)
            await _setActiveFlow(result.id);
    }
    else if (result.type === "step") {
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
    }
    else if (result.type === "agent") {
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
    }
    else if (result.type === "artifact") {
        if (_setActiveFlow && result.flow)
            await _setActiveFlow(result.flow);
    }
}
/**
 * Initialize search input handlers.
 */
export function initSearchHandlers() {
    const searchInput = document.getElementById("search-input");
    const dropdown = document.getElementById("search-dropdown");
    if (!searchInput)
        return;
    searchInput.addEventListener("input", (e) => {
        if (state.searchDebounceTimer) {
            clearTimeout(state.searchDebounceTimer);
        }
        const target = e.target;
        const query = target.value.trim();
        // Optimization: Increased debounce from 200ms to 300ms to reduce API calls while typing
        state.searchDebounceTimer = setTimeout(() => performSearch(query), 300);
    });
    searchInput.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            closeSearchDropdown();
            searchInput.blur();
        }
        else if (e.key === "ArrowDown") {
            e.preventDefault();
            if (state.searchResults.length > 0) {
                state.searchSelectedIndex = Math.min(state.searchSelectedIndex + 1, state.searchResults.length - 1);
                renderSearchResults(state.searchResults);
            }
        }
        else if (e.key === "ArrowUp") {
            e.preventDefault();
            if (state.searchResults.length > 0) {
                state.searchSelectedIndex = Math.max(state.searchSelectedIndex - 1, 0);
                renderSearchResults(state.searchResults);
            }
        }
        else if (e.key === "Enter") {
            e.preventDefault();
            if (state.searchSelectedIndex >= 0) {
                selectSearchResult(state.searchSelectedIndex);
            }
            else if (state.searchResults.length > 0) {
                selectSearchResult(0);
            }
        }
    });
    // Close dropdown when clicking outside
    document.addEventListener("click", (e) => {
        const target = e.target;
        if (!searchInput.contains(target) && dropdown && !dropdown.contains(target)) {
            closeSearchDropdown();
        }
    });
    // Clear button handler
    const clearButton = document.getElementById("search-clear");
    if (clearButton && searchInput) {
        clearButton.addEventListener("click", () => {
            searchInput.value = "";
            searchInput.focus();
            if (state.searchDebounceTimer) {
                clearTimeout(state.searchDebounceTimer);
                state.searchDebounceTimer = null;
            }
            performSearch("");
        });
    }
    // Event delegation for search results
    if (dropdown) {
        dropdown.addEventListener("click", (e) => {
            const target = e.target;
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
export function focusSearch() {
    const searchInput = document.getElementById("search-input");
    if (searchInput)
        searchInput.focus();
}
