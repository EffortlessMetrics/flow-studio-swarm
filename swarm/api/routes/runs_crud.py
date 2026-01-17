"""
Run CRUD endpoints for Flow Studio API.

Provides REST endpoints for:
- Starting new runs (POST /)
- Listing runs (GET /)
- Getting run state (GET /{run_id})
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Response
from fastapi.responses import JSONResponse

from ..services.run_state import get_state_manager
from .runs_models import (
    RunListResponse,
    RunStartRequest,
    RunStartResponse,
    RunSummary,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["runs"])


@router.post("", response_model=RunStartResponse, status_code=201)
async def start_run(request: RunStartRequest):
    """Start a new run.

    Creates a new run directory and initializes run state.
    Returns the run ID and SSE events URL.

    Args:
        request: Run start request with flow_id and optional parameters.

    Returns:
        RunStartResponse with run_id and events_url.
    """
    state_manager = get_state_manager()

    try:
        state = await state_manager.create_run(
            flow_id=request.flow_id,
            run_id=request.run_id,
            context=request.context,
            start_step=request.start_step,
        )

        return RunStartResponse(
            run_id=state["run_id"],
            flow_id=state["flow_id"],
            status=state["status"],
            created_at=state["created_at"],
            events_url=f"/api/runs/{state['run_id']}/events",
        )

    except Exception as e:
        logger.error("Failed to start run: %s", e)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "run_start_failed",
                "message": str(e),
                "details": {},
            },
        )


@router.get("", response_model=RunListResponse)
async def list_runs(limit: int = 20):
    """List recent runs.

    Args:
        limit: Maximum number of runs to return.

    Returns:
        List of run summaries.
    """
    state_manager = get_state_manager()
    runs = state_manager.list_runs(limit=limit)
    return RunListResponse(runs=[RunSummary(**r) for r in runs])


@router.get("/{run_id}")
async def get_run(
    run_id: str,
    if_none_match: Optional[str] = Header(None, alias="If-None-Match"),
):
    """Get run state.

    Args:
        run_id: Run identifier.
        if_none_match: Optional ETag for caching.

    Returns:
        Run state with ETag header.

    Raises:
        404: Run not found.
        304: Not modified (if ETag matches).
    """
    state_manager = get_state_manager()

    try:
        state, etag = await state_manager.get_run(run_id)

        # Check If-None-Match for caching
        if if_none_match and if_none_match.strip('"') == etag:
            return Response(status_code=304)

        return JSONResponse(
            content=state,
            headers={"ETag": f'"{etag}"'},
        )

    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "run_not_found",
                "message": f"Run '{run_id}' not found",
                "details": {"run_id": run_id},
            },
        )
