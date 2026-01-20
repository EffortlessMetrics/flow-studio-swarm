from __future__ import annotations

import datetime
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from ..deps import get_state
from ..state import FlowStudioState
from ..ui.index import get_index_html

try:
    from swarm.flowstudio import schema
except ImportError:
    schema = None

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index() -> str:
    return get_index_html()


@router.get("/api/health", response_model=schema.HealthStatus if schema else None)
async def api_health(state: FlowStudioState = Depends(get_state)) -> dict[str, Any]:
    if state.core:
        flows = state.core.list_flows()
        agents_count = len(state.agents_cache)
    else:
        flows = []
        agents_count = 0

    selftest_status = None
    try:
        if state.core:
            status = state.core.get_validation_snapshot()
            if hasattr(status, "selftest_summary"):
                selftest_status = status.selftest_summary
    except Exception:
        pass

    return {
        "status": "ok",
        "version": "2.0.0",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "flows": len(flows),
        "agents": agents_count,
        "selftest_status": selftest_status,
        "capabilities": {
            "runs": state.run_inspector is not None,
            "timeline": state.run_inspector is not None,
            "governance": state.core is not None,
            "validation": state.validation_data is not None,
        },
    }


@router.post("/api/reload", response_model=schema.ReloadResponse if schema else None)
async def api_reload(state: FlowStudioState = Depends(get_state)) -> dict[str, Any]:
    """Force reload all data from disk.

    Reloads all flow specs, agent configurations, and cached data from disk.
    Use this after making external modifications to configuration files.

    Returns:
        ReloadResponse with reload status and counts.
    """
    try:
        # Reload state caches
        state.reload_from_disk()

        # Get updated counts
        if state.core:
            flows_count = len(state.core.list_flows())
        else:
            flows_count = 0
        agents_count = len(state.agents_cache)

        return {
            "status": "ok",
            "flows": flows_count,
            "agents": agents_count,
        }
    except Exception as e:
        return {
            "status": f"error: {str(e)}",
            "flows": 0,
            "agents": 0,
        }
