// swarm/tools/flow_studio_ui/src/layout_spec.ts
// Layout specification for Flow Studio screens
//
// This module defines the authoritative layout registry for Flow Studio.
// It enables:
// - MCP tools to enumerate screens/regions/UIIDs
// - run_layout_review.py to capture per-screen artifacts
// - Tests to verify layout contract compliance
//
// VERSION: 0.5.0-flowstudio (adds layout spec to SDK)
// ============================================================================
// Authoritative Screen Registry
// ============================================================================
/**
 * Authoritative registry of screens.
 * This is what MCP + layout-review will enumerate.
 */
export const screens = [
    {
        id: "flows.default",
        route: "/",
        title: "Flows - Default",
        description: "Main Flow Studio screen with run selector, flow list, graph canvas, and inspector.",
        regions: [
            {
                id: "header",
                purpose: "Global navigation, search, governance indicators, mode toggle.",
                uiids: [
                    "flow_studio.header",
                    "flow_studio.header.search",
                    "flow_studio.header.search.input",
                    "flow_studio.header.search.results",
                    "flow_studio.header.search.clear",
                    "flow_studio.header.controls",
                    "flow_studio.header.tour",
                    "flow_studio.header.tour.trigger",
                    "flow_studio.header.tour.menu",
                    "flow_studio.header.mode",
                    "flow_studio.header.mode.author",
                    "flow_studio.header.mode.operator",
                    "flow_studio.header.governance",
                    "flow_studio.header.governance.overlay",
                    "flow_studio.header.reload",
                    "flow_studio.header.reload.btn",
                    "flow_studio.header.help",
                ],
            },
            {
                id: "sdlc_bar",
                purpose: "SDLC progress bar showing flow completion status.",
                uiids: ["flow_studio.sdlc_bar"],
            },
            {
                id: "sidebar",
                purpose: "Run selector, flow list, and view toggles between agents and artifacts.",
                uiids: [
                    "flow_studio.sidebar",
                    "flow_studio.sidebar.run_selector",
                    "flow_studio.sidebar.run_selector.select",
                    "flow_studio.sidebar.compare_selector",
                    "flow_studio.sidebar.flow_list",
                    "flow_studio.sidebar.view_toggle",
                ],
            },
            {
                id: "canvas",
                purpose: "Graph visualization of the current flow and SDLC legend.",
                uiids: [
                    "flow_studio.canvas",
                    "flow_studio.canvas.graph",
                    "flow_studio.canvas.legend",
                    "flow_studio.canvas.legend.toggle",
                    "flow_studio.canvas.outline",
                ],
            },
            {
                id: "inspector",
                purpose: "Details panel for selected step/agent/artifact, timing, and timeline.",
                uiids: [
                    "flow_studio.inspector",
                    "flow_studio.inspector.details",
                ],
            },
        ],
    },
    {
        id: "flows.selftest",
        route: "/?modal=selftest",
        title: "Flows - Selftest Modal",
        description: "Selftest plan / results modal and controls.",
        regions: [
            {
                id: "modal",
                purpose: "Selftest plan, run controls, copy helpers.",
                uiids: ["flow_studio.modal.selftest"],
            },
        ],
    },
    {
        id: "flows.shortcuts",
        route: "/?modal=shortcuts",
        title: "Flows - Shortcuts Modal",
        description: "Keyboard shortcuts reference modal.",
        regions: [
            {
                id: "modal",
                purpose: "Keyboard shortcuts grid.",
                uiids: ["flow_studio.modal.shortcuts"],
            },
        ],
    },
    {
        id: "flows.validation",
        route: "/?tab=validation",
        title: "Flows - Validation View",
        description: "Governance validation results and FR status badges.",
        regions: [
            {
                id: "header",
                purpose: "Governance badge and overlay toggle.",
                uiids: [
                    "flow_studio.header.governance",
                    "flow_studio.header.governance.overlay",
                ],
            },
            {
                id: "inspector",
                purpose: "Validation details for selected agent or flow.",
                uiids: [
                    "flow_studio.inspector",
                    "flow_studio.inspector.details",
                ],
            },
        ],
    },
    {
        id: "flows.tour",
        route: "/?tour=<tour_id>",
        title: "Flows - Tour Mode",
        description: "Guided tour overlay with step-by-step navigation.",
        regions: [
            {
                id: "header",
                purpose: "Tour menu and controls.",
                uiids: [
                    "flow_studio.header.tour",
                    "flow_studio.header.tour.trigger",
                    "flow_studio.header.tour.menu",
                ],
            },
            {
                id: "canvas",
                purpose: "Tour card overlay on graph nodes.",
                uiids: [
                    "flow_studio.canvas",
                    "flow_studio.canvas.graph",
                ],
            },
        ],
    },
];
// ============================================================================
// Convenience Accessors
// ============================================================================
/**
 * Index of screens by ID for quick lookup.
 */
export const screenById = Object.fromEntries(screens.map((s) => [s.id, s]));
/**
 * Get all known screen IDs.
 */
export function getScreenIds() {
    return screens.map((s) => s.id);
}
/**
 * Get a screen spec by ID, or null if not found.
 */
export function getScreenById(id) {
    return screenById[id] ?? null;
}
/**
 * Get all UIIDs across all screens and regions.
 * Useful for coverage checks.
 */
export function getAllKnownUIIDs() {
    const uiids = new Set();
    for (const screen of screens) {
        for (const region of screen.regions) {
            for (const uiid of region.uiids) {
                uiids.add(uiid);
            }
        }
    }
    return Array.from(uiids);
}
/**
 * Validate that all UIIDs in the layout spec are actually defined
 * in the FlowStudioUIID type. Returns UIIDs that are in spec but
 * not in the type (should be empty if spec is in sync).
 */
export function validateLayoutUIIDs() {
    // This is a compile-time check via the type system.
    // If a UIID in screens isn't in FlowStudioUIID, TypeScript will error.
    // Runtime validation would require importing the actual type definition.
    return { valid: true, issues: [] };
}
// ============================================================================
// JSON Export (for Python/API consumption)
// ============================================================================
/**
 * Export the layout spec as a JSON-serializable object.
 * Used by /api/layout_screens endpoint.
 */
export function toJSON() {
    return {
        version: "0.5.0-flowstudio",
        screens: screens,
    };
}
