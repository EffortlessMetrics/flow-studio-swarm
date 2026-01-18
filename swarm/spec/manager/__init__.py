"""
manager package - Central SpecManager for spec file management.
"""

from __future__ import annotations

from .core import SpecManager, get_manager, reset_manager
from .errors import ConcurrencyError, SpecError, SpecNotFoundError, SpecValidationError
from .models import FlowGraph, StepTemplate, ValidationError, ValidationResult
from .overlay import (
    FlowSpecManager,
    get_flow_manager,
    load_flow_graph,
    load_ui_overlay,
    list_flows,
    merge_flow_with_overlay,
    shred_flow_update,
)

__all__ = [
    "SpecManager",
    "FlowSpecManager",
    "FlowGraph",
    "StepTemplate",
    "ValidationError",
    "ValidationResult",
    "SpecError",
    "SpecNotFoundError",
    "SpecValidationError",
    "ConcurrencyError",
    "get_manager",
    "reset_manager",
    "get_flow_manager",
    "merge_flow_with_overlay",
    "shred_flow_update",
    "load_flow_graph",
    "load_ui_overlay",
    "list_flows",
]
