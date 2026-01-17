"""
Run control endpoints for Flow Studio API.

This module aggregates route modules for runs, autopilot, and issue ingestion.
The router is mounted at /runs by the server (prefix is managed externally).

For new development, import directly from the specific route modules:
- runs_crud: Run CRUD endpoints (start, list, get)
- runs_control: Run lifecycle endpoints (pause, resume, inject, interrupt, cancel, stop)
- runs_stack: Run stack inspection endpoints
- autopilot_routes: Autopilot start/stop/tick endpoints
- issue_routes: Issue ingestion endpoints

This module also re-exports commonly used types and functions for backward
compatibility with existing code.
"""

from __future__ import annotations

from fastapi import APIRouter

# Import sub-routers from split modules
from .autopilot_routes import router as autopilot_router
from .issue_routes import router as issue_router
from .runs_control import router as runs_control_router
from .runs_crud import router as runs_crud_router
from .runs_stack import router as runs_stack_router

# Create the main router that aggregates all sub-routers
# The server mounts this at /api. Prefixes are specified on include_router calls
# to avoid the "prefix and path cannot be both empty" FastAPI error.
router = APIRouter(tags=["runs"])

# Include sub-routers with explicit prefixes
# This allows sub-routers to use "" for collection root endpoints (e.g., GET /runs, POST /runs)
# without hitting the empty-prefix + empty-path FastAPI restriction.

# runs_crud handles /runs/* core CRUD endpoints (start, list, get)
router.include_router(runs_crud_router, prefix="/runs")

# runs_control handles /runs/{id}/* control endpoints (pause, resume, inject, etc.)
router.include_router(runs_control_router, prefix="/runs")

# runs_stack handles /runs/{id}/stack endpoint
router.include_router(runs_stack_router, prefix="/runs")

# autopilot_router handles /runs/autopilot/* endpoints
router.include_router(autopilot_router, prefix="/runs/autopilot")

# issue_router handles /runs/from-issue endpoint
router.include_router(issue_router, prefix="/runs")


# =============================================================================
# Backward Compatibility Exports
#
# These re-exports ensure existing code that imports from this module
# continues to work. New code should import directly from the source modules.
# =============================================================================

# Re-export RunStateManager and get_state_manager for backward compatibility
from ..services.run_state import RunStateManager, get_state_manager

# For backward compatibility, alias the old private function
_get_state_manager = get_state_manager

# Re-export Pydantic models from runs_models
from .runs_models import (
    InjectRequest,
    InterruptionFrameResponse,
    InterruptionStackResponse,
    InterruptRequest,
    PauseRequest,
    ResumeRequest,
    RunActionResponse,
    RunListResponse,
    RunStartRequest,
    RunStartResponse,
    RunState,
    RunSummary,
    StopReportInfo,
    StopRequest,
    StopResponse,
)

# Re-export Pydantic models from autopilot_routes
from .autopilot_routes import (
    AutopilotStartRequest,
    AutopilotStartResponse,
    AutopilotStatusResponse,
    AutopilotStopRequest,
    WisdomApplyResultResponse,
)

# Re-export Pydantic models from issue_routes
from .issue_routes import (
    IssueIngestionRequest,
    IssueIngestionResponse,
    IssueSnapshot,
)

# Re-export autopilot controller getter for backward compatibility
from .autopilot_routes import _get_autopilot_controller

__all__ = [
    # Main router
    "router",
    # Services
    "RunStateManager",
    "get_state_manager",
    "_get_state_manager",  # Deprecated alias
    # Run models
    "RunStartRequest",
    "RunStartResponse",
    "RunSummary",
    "RunListResponse",
    "RunState",
    "RunActionResponse",
    "InjectRequest",
    "InterruptRequest",
    "PauseRequest",
    "ResumeRequest",
    "StopRequest",
    "StopReportInfo",
    "StopResponse",
    "InterruptionFrameResponse",
    "InterruptionStackResponse",
    # Autopilot models
    "AutopilotStartRequest",
    "AutopilotStartResponse",
    "AutopilotStatusResponse",
    "AutopilotStopRequest",
    "WisdomApplyResultResponse",
    "_get_autopilot_controller",
    # Issue models
    "IssueIngestionRequest",
    "IssueIngestionResponse",
    "IssueSnapshot",
]
