"""Run creation and read endpoints for the canonical run service."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Response
from fastapi.responses import JSONResponse

from ..services.run_state import get_state_manager
from .runs_models import RunListResponse, RunStartRequest, RunStartResponse, RunSummary

logger = logging.getLogger(__name__)
router = APIRouter(tags=["runs"])
_VALID_MODES = frozenset({"execute", "preview", "validate"})


@router.post("", response_model=RunStartResponse, status_code=201)
async def start_run(request: RunStartRequest):
    """Create one complete durable run record under the returned identity."""
    if request.mode not in _VALID_MODES:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_mode",
                "message": f"Unsupported run mode '{request.mode}'",
                "details": {"valid_modes": sorted(_VALID_MODES)},
            },
        )

    state_manager = get_state_manager()
    try:
        state = await state_manager.create_run(
            flow_id=request.flow_id,
            run_id=request.run_id,
            context=request.context,
            start_step=request.start_step,
            mode=request.mode,
            backend=request.backend,
            initiator="api",
        )
    except FileExistsError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "run_exists",
                "message": str(exc),
                "details": {"run_id": request.run_id},
            },
        ) from exc
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_run_request",
                "message": str(exc),
                "details": {},
            },
        ) from exc
    except Exception as exc:
        logger.exception("Failed to initialize run")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "run_start_failed",
                "message": str(exc),
                "details": {},
            },
        ) from exc

    return RunStartResponse(
        run_id=state["run_id"],
        flow_id=state["flow_id"],
        status=state["status"],
        created_at=state["created_at"],
        events_url=f"/api/runs/{state['run_id']}/events",
    )


@router.get("", response_model=RunListResponse)
async def list_runs(limit: int = 20):
    state_manager = get_state_manager()
    runs = state_manager.list_runs(limit=limit)
    return RunListResponse(runs=[RunSummary(**run) for run in runs])


@router.get("/{run_id}")
async def get_run(
    run_id: str,
    if_none_match: Optional[str] = Header(None, alias="If-None-Match"),
):
    state_manager = get_state_manager()
    try:
        state, etag = await state_manager.get_run(run_id)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "run_not_found",
                "message": f"Run '{run_id}' not found",
                "details": {"run_id": run_id},
            },
        ) from exc

    if if_none_match and if_none_match.strip('"') == etag:
        return Response(status_code=304)

    return JSONResponse(content=state, headers={"ETag": f'"{etag}"'})
