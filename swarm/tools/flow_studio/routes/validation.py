from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from ..deps import get_state
from ..state import FlowStudioState

try:
    from swarm.flowstudio import schema
except ImportError:
    schema = None

router = APIRouter()


@router.get("/api/validation", response_model=schema.ValidationData if schema else None)
async def api_validation(state: FlowStudioState = Depends(get_state)):
    if state.validation_data is not None:
        return {"data": state.validation_data}
    return JSONResponse(
        {"data": None, "error": "validation data not available"},
        status_code=503,
    )
