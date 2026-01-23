from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .core import SpecManager
from .errors import ConcurrencyError, SpecNotFoundError, SpecValidationError
from .etag import compute_etag_bytes, compute_file_etag
from .io import atomic_write
from .models import ValidationError

logger = logging.getLogger(__name__)


class FlowSpecManager:
    """Manager for FlowGraph logic and UI overlay files."""

    def __init__(self, repo_root: Optional[Path] = None):
        """Initialize the FlowSpecManager.

        Args:
            repo_root: Repository root path. If None, attempts to auto-detect.
        """
        self._manager = SpecManager(repo_root=repo_root)
        self._flows_dir = self._manager.specs_dir / "flows"

    @property
    def flows_dir(self) -> Path:
        """Get the flows directory path."""
        return self._flows_dir

    def list_flows(self) -> List[str]:
        """List all available flow IDs."""
        if not self._flows_dir.exists():
            return []

        flow_ids = set()
        for json_file in self._flows_dir.glob("*.json"):
            if not json_file.name.endswith(".ui.json"):
                flow_ids.add(json_file.stem)

        return sorted(flow_ids)

    def load_flow_graph(self, flow_id: str) -> Dict[str, Any]:
        """Load just the logic graph (no UI overlay)."""
        path = self._flows_dir / f"{flow_id}.json"
        if not path.exists():
            raise SpecNotFoundError("flow_graph", flow_id, path)

        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise SpecValidationError(
                "flow_graph",
                [ValidationError(path="", message=f"Invalid JSON: {e}")],
            )

    def load_ui_overlay(self, flow_id: str) -> Optional[Dict[str, Any]]:
        """Load just the UI overlay."""
        path = self._flows_dir / f"{flow_id}.ui.json"
        if not path.exists():
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.warning("Invalid UI overlay JSON for %s: %s", flow_id, e)
            return None

    def merge_flow_with_overlay(self, flow_id: str) -> Tuple[Dict[str, Any], str]:
        """Merge flow graph with UI overlay for API response."""
        flow_data = self.load_flow_graph(flow_id)
        ui_data = self.load_ui_overlay(flow_id) or {}

        # Deep merge UI overlay into flow data
        merged = self._deep_merge_with_nodes(flow_data, ui_data)

        # Compute combined ETag
        flow_path = self._flows_dir / f"{flow_id}.json"
        ui_path = self._flows_dir / f"{flow_id}.ui.json"

        flow_etag = compute_file_etag(flow_path) or ""
        ui_etag = compute_file_etag(ui_path) or ""
        combined_etag = compute_etag_bytes(f"{flow_etag}:{ui_etag}".encode("utf-8"))

        return merged, combined_etag

    def _deep_merge_with_nodes(
        self, flow_data: Dict[str, Any], ui_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deep merge UI overlay into flow data, with special node handling."""
        merged = flow_data.copy()

        # Merge top-level UI-only keys
        for key in ["palette", "canvas", "groups", "annotations"]:
            if key in ui_data:
                merged[key] = ui_data[key]

        # Merge node-level UI data (positions, colors, etc.)
        if "nodes" in ui_data and "nodes" in merged:
            ui_nodes = ui_data["nodes"]
            if isinstance(ui_nodes, dict):
                # UI overlay uses {node_id: {position, color, ...}} format
                for i, node in enumerate(merged["nodes"]):
                    node_id = node.get("id")
                    if node_id and node_id in ui_nodes:
                        merged["nodes"][i] = {**node, **ui_nodes[node_id]}

        # Merge edge-level UI data
        if "edges" in ui_data and "edges" in merged:
            ui_edges = ui_data["edges"]
            if isinstance(ui_edges, dict):
                # UI overlay uses {from:to: {color, waypoints, ...}} format
                for i, edge in enumerate(merged["edges"]):
                    edge_key = f"{edge.get('from')}:{edge.get('to')}"
                    if edge_key in ui_edges:
                        merged["edges"][i] = {**edge, **ui_edges[edge_key]}

        return merged

    def shred_flow_update(
        self,
        flow_id: str,
        merged_data: Dict[str, Any],
        etag: Optional[str] = None,
    ) -> Tuple[str, str]:
        """Split merged data back into logic graph and UI overlay files."""
        if etag is not None:
            _, current_etag = self.merge_flow_with_overlay(flow_id)
            if current_etag != etag:
                raise ConcurrencyError("flow", flow_id, etag, current_etag)

        # Keys that belong in UI overlay
        ui_top_level_keys = {"palette", "canvas", "groups", "annotations", "version"}
        ui_node_keys = {
            "position",
            "size",
            "color",
            "icon",
            "collapsed",
            "pinned",
            "label_position",
            "custom_class",
        }
        ui_edge_keys = {
            "color",
            "stroke_width",
            "stroke_style",
            "label_visible",
            "waypoints",
        }

        # Split the data
        flow_data: Dict[str, Any] = {}
        ui_data: Dict[str, Any] = {"flow_id": flow_id}

        for key, value in merged_data.items():
            if key in ui_top_level_keys:
                ui_data[key] = value
            elif key == "nodes":
                flow_nodes = []
                ui_nodes = {}
                for node in value:
                    node_id = node.get("id")
                    flow_node = {}
                    ui_node = {}
                    for nk, nv in node.items():
                        if nk in ui_node_keys:
                            ui_node[nk] = nv
                        else:
                            flow_node[nk] = nv
                    flow_nodes.append(flow_node)
                    if ui_node:
                        ui_nodes[node_id] = ui_node
                flow_data["nodes"] = flow_nodes
                if ui_nodes:
                    ui_data["nodes"] = ui_nodes
            elif key == "edges":
                flow_edges = []
                ui_edges = {}
                for edge in value:
                    edge_key = f"{edge.get('from')}:{edge.get('to')}"
                    flow_edge = {}
                    ui_edge = {}
                    for ek, ev in edge.items():
                        if ek in ui_edge_keys:
                            ui_edge[ek] = ev
                        else:
                            flow_edge[ek] = ev
                    flow_edges.append(flow_edge)
                    if ui_edge:
                        ui_edges[edge_key] = ui_edge
                flow_data["edges"] = flow_edges
                if ui_edges:
                    ui_data["edges"] = ui_edges
            else:
                flow_data[key] = value

        # Ensure directory exists
        self._flows_dir.mkdir(parents=True, exist_ok=True)

        # Write flow graph
        flow_path = self._flows_dir / f"{flow_id}.json"
        flow_content = json.dumps(flow_data, indent=2, ensure_ascii=False) + "\n"
        atomic_write(flow_path, flow_content, logger=logger)
        flow_etag = compute_etag_bytes(flow_content.encode("utf-8"))

        # Write UI overlay (only if there's UI data beyond flow_id)
        ui_etag = ""
        ui_path = self._flows_dir / f"{flow_id}.ui.json"
        if len(ui_data) > 1:
            ui_content = json.dumps(ui_data, indent=2, ensure_ascii=False) + "\n"
            atomic_write(ui_path, ui_content, logger=logger)
            ui_etag = compute_etag_bytes(ui_content.encode("utf-8"))

        logger.info(
            "Shredded flow update: %s (flow_etag: %s, ui_etag: %s)",
            flow_id,
            flow_etag[:12],
            ui_etag[:12] if ui_etag else "none",
        )

        return flow_etag, ui_etag


_default_flow_manager: Optional[FlowSpecManager] = None


def get_flow_manager(repo_root: Optional[Path] = None) -> FlowSpecManager:
    """Get or create the default FlowSpecManager."""
    global _default_flow_manager
    if _default_flow_manager is None:
        _default_flow_manager = FlowSpecManager(repo_root=repo_root)
    return _default_flow_manager


def merge_flow_with_overlay(flow_id: str) -> Tuple[Dict[str, Any], str]:
    """Merge flow graph with UI overlay for API response."""
    return get_flow_manager().merge_flow_with_overlay(flow_id)


def shred_flow_update(
    flow_id: str,
    merged_data: Dict[str, Any],
    etag: Optional[str] = None,
) -> Tuple[str, str]:
    """Split merged data back into logic graph and UI overlay files."""
    return get_flow_manager().shred_flow_update(flow_id, merged_data, etag)


def load_flow_graph(flow_id: str) -> Dict[str, Any]:
    """Load just the flow logic graph (no UI overlay)."""
    return get_flow_manager().load_flow_graph(flow_id)


def load_ui_overlay(flow_id: str) -> Optional[Dict[str, Any]]:
    """Load just the UI overlay for a flow."""
    return get_flow_manager().load_ui_overlay(flow_id)


def list_flows() -> List[str]:
    """List all available flow IDs."""
    return get_flow_manager().list_flows()
