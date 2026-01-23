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


@router.get("/api/tours", response_model=schema.ToursListResponse if schema else None)
async def api_tours(state: FlowStudioState = Depends(get_state)):
    tours = []
    for tour in state.tours_cache.values():
        tours.append(
            {
                "id": tour["id"],
                "title": tour["title"],
                "description": tour["description"],
                "step_count": len(tour["steps"]),
            }
        )
    return {"tours": tours}


@router.get("/api/tours/{tour_id}", response_model=schema.TourDetail if schema else None)
async def api_tour_detail(tour_id: str, state: FlowStudioState = Depends(get_state)):
    tour = state.tours_cache.get(tour_id)
    if not tour:
        available = sorted(state.tours_cache.keys())
        return JSONResponse(
            {
                "error": f"Tour '{tour_id}' not found",
                "available_tours": available,
                "hint": f"Available tours: {', '.join(available)}"
                if available
                else "No tours loaded",
            },
            status_code=404,
        )

    steps = []
    for step in tour["steps"]:
        steps.append(
            {
                "target": {
                    "type": step["target_type"],
                    "flow": step["target_flow"],
                    "step": step["target_step"],
                },
                "title": step["title"],
                "text": step["text"],
                "action": step["action"],
            }
        )

    return {
        "id": tour["id"],
        "title": tour["title"],
        "description": tour["description"],
        "steps": steps,
    }
