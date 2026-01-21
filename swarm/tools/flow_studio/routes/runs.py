from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from ..deps import get_state
from ..services.run_artifacts import (
    RunArtifactsError,
    load_receipt,
    load_transcript,
    load_wisdom_summary,
)
from ..services.run_service import (
    cancel_run,
    get_events,
    list_backends,
    list_exemplars,
    list_runs,
    mark_exemplar,
    start_run,
)
from ..state import FlowStudioState

try:
    from swarm.flowstudio import schema
except ImportError:
    schema = None

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/api/runs", response_model=schema.RunsListResponse if schema else None)
async def api_runs(
    limit: int = 100,
    offset: int = 0,
    state: FlowStudioState = Depends(get_state),
):
    limit = max(1, min(limit, 500))
    offset = max(0, offset)

    def _fetch_runs():
        all_runs_inner = []

        if state.run_service is not None:
            try:
                all_runs_inner = list_runs(state.run_service)
            except Exception as exc:
                logger.warning(
                    "RunService.list_runs failed, falling back to legacy inspector: %s",
                    exc,
                    exc_info=True,
                )
                all_runs_inner = []

        if not all_runs_inner and state.core:
            all_runs_inner = state.core.list_runs()

        return all_runs_inner

    try:
        all_runs = await run_in_threadpool(_fetch_runs)
    except Exception:
        return JSONResponse(
            {
                "error": "Run inspector not available",
                "runs": [],
                "total": 0,
                "limit": limit,
                "offset": offset,
                "has_more": False,
            },
            status_code=503,
        )

    total = len(all_runs)
    paginated_runs = all_runs[offset : offset + limit]
    has_more = (offset + limit) < total

    return {
        "runs": paginated_runs,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": has_more,
    }


@router.get("/api/runs/{run_id}/summary", response_model=schema.RunSummary if schema else None)
async def api_run_summary(run_id: str, state: FlowStudioState = Depends(get_state)):
    if not state.core:
        return JSONResponse({"error": "Run inspector not available"}, status_code=503)

    try:
        summary = state.core.get_run_summary(run_id)
        return summary.to_dict()
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@router.get("/api/backends", response_model=schema.BackendsListResponse if schema else None)
async def api_backends(state: FlowStudioState = Depends(get_state)):
    if state.run_service is None:
        return JSONResponse(
            {"error": "RunService not available", "backends": []},
            status_code=503,
        )

    try:
        backends = list_backends(state.run_service)
        return {"backends": backends}
    except Exception as exc:
        return JSONResponse({"error": str(exc), "backends": []}, status_code=500)


@router.post("/api/run", response_model=schema.StartRunResponse if schema else None)
async def api_start_run(
    request: schema.StartRunRequest if schema else None,
    state: FlowStudioState = Depends(get_state),
):
    if state.run_service is None:
        return JSONResponse({"error": "RunService not available"}, status_code=503)

    if request is None:
        return JSONResponse(
            {"error": "Request body required", "run_id": None, "status": "error"},
            status_code=400,
        )

    try:
        run_id = start_run(state.run_service, request.flows, request.profile_id, request.backend)
        logger.info("Started run %s with flows: %s", run_id, request.flows)
        return {
            "run_id": run_id,
            "status": "started",
            "message": f"Run {run_id} started with flows: {', '.join(request.flows)}",
        }
    except ValueError as exc:
        logger.warning("Invalid run request: %s", exc)
        return JSONResponse(
            {"error": str(exc), "run_id": None, "status": "error"},
            status_code=400,
        )
    except Exception as exc:
        logger.exception("Failed to start run")
        return JSONResponse(
            {"error": str(exc), "run_id": None, "status": "error"},
            status_code=500,
        )


@router.get(
    "/api/runs/{run_id}/events", response_model=schema.RunEventsResponse if schema else None
)
async def api_run_events(run_id: str, state: FlowStudioState = Depends(get_state)):
    if state.run_service is None:
        return JSONResponse({"error": "RunService not available"}, status_code=503)

    try:
        return {"run_id": run_id, "events": get_events(state.run_service, run_id)}
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@router.get("/api/runs/{run_id}/flows/{flow_key}/steps/{step_id}/transcript")
async def api_step_transcript(
    run_id: str,
    flow_key: str,
    step_id: str,
    state: FlowStudioState = Depends(get_state),
):
    try:
        return load_transcript(run_id, flow_key, step_id, state.run_inspector)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    except RunArtifactsError as exc:
        return JSONResponse(exc.payload, status_code=exc.status_code)


@router.get("/api/runs/{run_id}/flows/{flow_key}/steps/{step_id}/receipt")
async def api_step_receipt(
    run_id: str,
    flow_key: str,
    step_id: str,
    state: FlowStudioState = Depends(get_state),
):
    try:
        return load_receipt(run_id, flow_key, step_id, state.run_inspector)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    except RunArtifactsError as exc:
        return JSONResponse(exc.payload, status_code=exc.status_code)


@router.post("/api/runs/{run_id}/cancel")
async def api_cancel_run(run_id: str, state: FlowStudioState = Depends(get_state)):
    if state.run_service is None:
        return JSONResponse({"error": "RunService not available"}, status_code=503)

    try:
        cancelled = cancel_run(state.run_service, run_id)
        if cancelled:
            return {"status": "cancelled", "run_id": run_id}
        return JSONResponse(
            {"error": "Run not found or already completed", "run_id": run_id},
            status_code=404,
        )
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@router.post("/api/runs/{run_id}/exemplar")
async def api_set_exemplar(
    run_id: str,
    is_exemplar: bool = Query(True),
    state: FlowStudioState = Depends(get_state),
):
    if state.run_service is None:
        return JSONResponse({"error": "RunService not available"}, status_code=503)

    try:
        success = mark_exemplar(state.run_service, run_id, is_exemplar)
        if success:
            return {
                "status": "updated",
                "run_id": run_id,
                "is_exemplar": is_exemplar,
            }
        return JSONResponse({"error": "Run not found", "run_id": run_id}, status_code=404)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@router.get("/api/runs/exemplars")
async def api_list_exemplars(state: FlowStudioState = Depends(get_state)):
    if state.run_service is None:
        return JSONResponse(
            {"error": "RunService not available", "runs": []},
            status_code=503,
        )

    try:
        return {"runs": list_exemplars(state.run_service)}
    except Exception as exc:
        return JSONResponse({"error": str(exc), "runs": []}, status_code=500)


@router.get("/api/runs/{run_id}/wisdom/summary")
async def api_run_wisdom_summary(run_id: str, state: FlowStudioState = Depends(get_state)):
    try:
        return load_wisdom_summary(run_id, state.run_inspector)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    except RunArtifactsError as exc:
        return JSONResponse(exc.payload, status_code=exc.status_code)


@router.get("/api/runs/{run_id}/sdlc", response_model=schema.SDLCBarResponse if schema else None)
async def api_run_sdlc(run_id: str, state: FlowStudioState = Depends(get_state)):
    if state.run_inspector is None:
        return JSONResponse({"error": "Run inspector not available"}, status_code=503)

    try:
        bar = state.run_inspector.get_sdlc_bar(run_id)
        return {"run_id": run_id, "sdlc": bar}
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@router.get(
    "/api/runs/{run_id}/flows/{flow_key}", response_model=schema.FlowStatusInfo if schema else None
)
async def api_run_flow(run_id: str, flow_key: str, state: FlowStudioState = Depends(get_state)):
    if state.run_inspector is None:
        return JSONResponse({"error": "Run inspector not available"}, status_code=503)

    try:
        result = state.run_inspector.get_flow_status(run_id, flow_key)
        return state.run_inspector.to_dict(result)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@router.get(
    "/api/runs/{run_id}/flows/{flow_key}/steps/{step_id}",
    response_model=schema.StepStatusInfo if schema else None,
)
async def api_run_step(
    run_id: str,
    flow_key: str,
    step_id: str,
    state: FlowStudioState = Depends(get_state),
):
    if state.run_inspector is None:
        return JSONResponse({"error": "Run inspector not available"}, status_code=503)

    try:
        result = state.run_inspector.get_step_status(run_id, flow_key, step_id)

        step_timing = None
        flow_timing = state.run_inspector.get_flow_timing(run_id, flow_key)
        if flow_timing:
            for step in flow_timing.steps:
                if step.step_id == step_id:
                    step_timing = state.run_inspector.to_dict(step)
                    break

        step_dict = state.run_inspector.to_dict(result)
        step_dict["timing"] = step_timing
        return step_dict
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@router.get(
    "/api/runs/{run_id}/timeline", response_model=schema.TimelineResponse if schema else None
)
async def api_run_timeline(run_id: str, state: FlowStudioState = Depends(get_state)):
    if state.run_inspector is None:
        return JSONResponse({"error": "RunInspector not available"}, status_code=503)

    try:
        timeline = state.run_inspector.get_run_timeline(run_id)
        return {"run_id": run_id, "events": [state.run_inspector.to_dict(e) for e in timeline]}
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@router.get(
    "/api/runs/{run_id}/timing", response_model=schema.RunTimingResponse if schema else None
)
async def api_run_timing(run_id: str, state: FlowStudioState = Depends(get_state)):
    if state.run_inspector is None:
        return JSONResponse({"error": "RunInspector not available"}, status_code=503)

    try:
        timing = state.run_inspector.get_run_timing(run_id)
        if timing is None:
            return {"run_id": run_id, "timing": None, "message": "No timing data available"}

        return {"run_id": run_id, "timing": state.run_inspector.to_dict(timing)}
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@router.get(
    "/api/runs/{run_id}/flows/{flow_key}/timing",
    response_model=schema.FlowTimingResponse if schema else None,
)
async def api_flow_timing(run_id: str, flow_key: str, state: FlowStudioState = Depends(get_state)):
    if state.run_inspector is None:
        return JSONResponse({"error": "RunInspector not available"}, status_code=503)

    try:
        timing = state.run_inspector.get_flow_timing(run_id, flow_key)
        if timing is None:
            return {
                "run_id": run_id,
                "flow_key": flow_key,
                "timing": None,
                "message": "No timing data available",
            }

        return {
            "run_id": run_id,
            "flow_key": flow_key,
            "timing": state.run_inspector.to_dict(timing),
        }
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@router.get("/api/runs/compare", response_class=JSONResponse)
async def api_runs_compare(
    run_a: str = Query(None, description="First run identifier (baseline)"),
    run_b: str = Query(None, description="Second run identifier (comparison target)"),
    flow: str = Query(None, description="Flow key to compare"),
    state: FlowStudioState = Depends(get_state),
):
    if state.run_inspector is None:
        return JSONResponse({"error": "Run inspector not available"}, status_code=503)

    if not run_a or not run_b or not flow:
        return JSONResponse(
            {"error": "Missing required parameters: run_a, run_b, flow"},
            status_code=400,
        )

    try:
        if state.run_inspector.get_run_path(run_a) is None:
            return JSONResponse({"error": f"Run '{run_a}' not found"}, status_code=404)

        if state.run_inspector.get_run_path(run_b) is None:
            return JSONResponse({"error": f"Run '{run_b}' not found"}, status_code=404)

        if flow not in state.run_inspector.catalog.get("flows", {}):
            return JSONResponse(
                {"error": f"Flow '{flow}' not found in catalog"},
                status_code=404,
            )

        result = state.run_inspector.compare_flows(run_a, run_b, flow)
        return result
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)
