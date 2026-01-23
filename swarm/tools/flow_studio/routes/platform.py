from __future__ import annotations

import os
import sys

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from ..deps import get_state
from ..state import FlowStudioState

try:
    from swarm.flowstudio import schema
except ImportError:
    schema = None

router = APIRouter()


@router.get("/platform/status", response_model=schema.ValidationSnapshot if schema else None)
async def platform_status(state: FlowStudioState = Depends(get_state)):
    if not state.core:
        return JSONResponse(
            {
                "error": "Status provider not available",
                "timestamp": None,
                "service": "flow-studio",
            },
            status_code=503,
        )

    try:
        status = await run_in_threadpool(state.core.get_validation_snapshot)
        return status.to_dict()
    except Exception as exc:
        return JSONResponse(
            {
                "error": f"Failed to compute status: {str(exc)}",
                "service": "flow-studio",
            },
            status_code=500,
        )


@router.post(
    "/platform/status/refresh", response_model=schema.ValidationSnapshot if schema else None
)
async def platform_status_refresh(state: FlowStudioState = Depends(get_state)):
    if not state.core:
        return JSONResponse(
            {
                "error": "Status provider not available",
                "timestamp": None,
                "service": "flow-studio",
            },
            status_code=503,
        )

    def _do_refresh():
        if hasattr(state.core, "_status_provider") and state.core._status_provider:
            status = state.core._status_provider.get_status(force_refresh=True)
            from swarm.flowstudio.core import ValidationSnapshot

            return ValidationSnapshot(
                timestamp=status.timestamp,
                service=status.service,
                governance=status.governance,
                flows=status.flows if hasattr(status, "flows") else {},
                agents=status.agents if hasattr(status, "agents") else {},
                hints=status.hints if hasattr(status, "hints") else {},
            ).to_dict()

        status = state.core.get_validation_snapshot()
        return status.to_dict()

    try:
        result = await run_in_threadpool(_do_refresh)
        return result
    except Exception as exc:
        return JSONResponse(
            {
                "error": f"Failed to compute status: {str(exc)}",
                "service": "flow-studio",
            },
            status_code=500,
        )


@router.get("/api/selftest/plan", response_model=schema.SelftestPlanResponse if schema else None)
async def api_selftest_plan():
    try:
        tools_path = str(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
        if tools_path not in sys.path:
            sys.path.insert(0, tools_path)

        from swarm.tools.selftest import get_selftest_plan_json

        plan = get_selftest_plan_json()
        return plan
    except (ImportError, SystemExit):
        return JSONResponse({"error": "Selftest module not available"}, status_code=503)
    except Exception as exc:
        return JSONResponse(
            {"error": f"Failed to get selftest plan: {str(exc)}"},
            status_code=500,
        )
