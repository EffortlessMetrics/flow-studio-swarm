// swarm/tools/flow_studio_ui/src/graph.ts
// Cytoscape graph management for Flow Studio
//
// This module handles:
// - Cytoscape instance creation and configuration
// - Graph rendering (nodes, edges, layout)
// - Node tap event handling via callbacks

import { state } from "./state.js";
import type {
  FlowGraph,
  NodeData,
  CytoscapeInstance,
  CytoscapeNodeCollection,
  RenderGraphOptions,
  FocusNodeOptions,
} from "./domain.js";

// ============================================================================
// CSS Token Helpers
// ============================================================================

/**
 * Get the graph edge color from CSS token.
 * Falls back to default if DOM not available or token not set.
 */
function getGraphEdgeColor(): string {
  try {
    const root = document.documentElement;
    const value = getComputedStyle(root)
      .getPropertyValue("--fs-color-graph-edge")
      .trim();
    return value || "#818cf8";
  } catch {
    return "#818cf8";
  }
}

// ============================================================================
// Cytoscape Style Configuration
// ============================================================================

/**
 * Build graph styles with resolved CSS tokens.
 * Called at runtime when DOM is available.
 */
function getGraphStyles(): CytoscapeStylesheet[] {
  const edgeColor = getGraphEdgeColor();
  return [
  {
    selector: 'node[type = "step"]',
    style: {
      "background-color": "#0f766e",
      "label": "data(label)",
      "text-valign": "center",
      "text-halign": "center",
      "color": "#ffffff",
      "font-size": 10,
      "shape": "round-rectangle",
      "padding": "6px",
      "width": "label",
      "height": "label",
      "border-width": 2,
      "border-color": "#134e4a"
    }
  },
  {
    selector: 'node[type = "agent"]',
    style: {
      "background-color": "data(color)",
      "label": "data(label)",
      "text-valign": "center",
      "text-halign": "center",
      "color": "#111827",
      "font-size": 10,
      "shape": "round-rectangle",
      "padding": "5px",
      "width": "label",
      "height": "label",
      "border-width": 2,
      "border-color": "#374151",
      "text-opacity": 1
    }
  },
  {
    selector: "edge",
    style: {
      "width": 2,
      "line-color": edgeColor,
      "target-arrow-color": edgeColor,
      "target-arrow-shape": "triangle",
      "curve-style": "bezier"
    }
  },
  {
    selector: 'edge[type = "step-sequence"]',
    style: {
      "line-style": "solid"
    }
  },
  {
    selector: 'edge[type = "step-agent"]',
    style: {
      "line-style": "dotted"
    }
  },
  {
    selector: 'node[type = "artifact"]',
    style: {
      "background-color": "#9ca3af",
      "label": "data(label)",
      "text-valign": "center",
      "text-halign": "center",
      "color": "#111827",
      "font-size": 9,
      "shape": "round-rectangle",
      "padding": "4px",
      "width": "label",
      "height": "label",
      "border-width": 2,
      "border-color": "#6b7280",
      "text-opacity": 1
    }
  },
  {
    selector: 'node[type = "artifact"][status = "present"]',
    style: {
      "background-color": "#22c55e"
    }
  },
  {
    selector: 'node[type = "artifact"][status = "missing"]',
    style: {
      "background-color": "#ef4444"
    }
  },
  {
    selector: 'node[type = "artifact"][is_decision]',
    style: {
      "border-width": 3,
      "border-color": "#3b82f6"
    }
  },
  {
    selector: 'edge[type = "step-artifact"]',
    style: {
      "line-style": "dotted"
    }
  }
  ];
}

interface LayoutOptions {
  name: string;
  directed?: boolean;
  padding?: number;
  [key: string]: unknown;
}

const DEFAULT_LAYOUT: LayoutOptions = {
  name: "breadthfirst",
  directed: true,
  padding: 16
};

// ============================================================================
// Module State
// ============================================================================

let nodeClickHandler: ((nodeData: NodeData) => void) | null = null;

// ============================================================================
// Public API
// ============================================================================

/**
 * Initialize the Cytoscape graph instance.
 * Safe to call multiple times - returns existing instance if already initialized.
 */
export function initGraph(options: RenderGraphOptions = {}): CytoscapeInstance {
  if (options.onNodeClick) {
    nodeClickHandler = options.onNodeClick;
  }

  if (state.cy) {
    return state.cy;
  }

  state.cy = cytoscape({
    container: document.getElementById("graph"),
    elements: { nodes: [], edges: [] },
    layout: DEFAULT_LAYOUT,
    style: getGraphStyles()
  });

  // Set up node tap handler
  state.cy.on("tap", (ev) => {
    if (!nodeClickHandler) return;
    // Check if target has a data method (it's a node)
    const target = ev.target;
    if (target && typeof target.data === "function") {
      const data = target.data() as NodeData;
      nodeClickHandler(data);
    }
  });

  return state.cy;
}

/**
 * Render a graph with the given nodes and edges.
 * Initializes Cytoscape if not already done.
 */
export function renderGraphCore(graph: FlowGraph, options: RenderGraphOptions = {}): CytoscapeInstance {
  const cy = initGraph(options);

  // Combine nodes and edges into a single array for batch addition
  const elements = [
    ...(graph.nodes || []),
    ...(graph.edges || [])
  ];

  // Optimization: Removed useless cy.elements().forEach() loop here
  // which was iterating over all elements for no reason before removal.

  cy.remove(cy.elements());
  cy.add(elements);
  cy.layout(DEFAULT_LAYOUT).run();

  return cy;
}

/**
 * Get the current Cytoscape instance.
 */
export function getCy(): CytoscapeInstance | null {
  return state.cy;
}

/**
 * Update the node click handler.
 * Useful when you need to change behavior after initialization.
 */
export function setNodeClickHandler(handler: (nodeData: NodeData) => void): void {
  nodeClickHandler = handler;
}

/**
 * Fit the graph view to a specific node with animation.
 */
export function focusNode(nodeId: string, options: FocusNodeOptions = {}): void {
  const { padding = 50 } = options;
  if (!state.cy) return;
  const node = state.cy.getElementById(nodeId);
  if (node) {
    state.cy.fit(padding);
    node.select();
  }
}

/**
 * Get step nodes sorted by their order.
 */
export function getStepNodesSorted(): CytoscapeNodeCollection | [] {
  if (!state.cy) return [];
  return state.cy.nodes('[type = "step"]').sort((a, b) => {
    const orderA = a.data("order") as number;
    const orderB = b.data("order") as number;
    return orderA - orderB;
  });
}
