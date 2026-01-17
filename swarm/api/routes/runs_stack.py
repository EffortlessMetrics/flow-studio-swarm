"""
Run stack inspection endpoint for Flow Studio API.

Provides REST endpoint for:
- Getting interruption stack (GET /{run_id}/stack)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from ..services.run_state import get_state_manager
from .runs_models import (
    InterruptionFrameResponse,
    InterruptionStackResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["runs"])


@router.get("/{run_id}/stack", response_model=InterruptionStackResponse)
async def get_interruption_stack(run_id: str):
    """Get the current interruption stack for a run.

    Returns the stack of interruption frames representing paused execution
    contexts during flow injection/detour operations.

    The response includes both:
    - frames: Structured InterruptionFrame data from RunState
    - detours: Simplified format compatible with InterruptionStackPanel.ts

    Args:
        run_id: Run identifier.

    Returns:
        InterruptionStackResponse with stack depth and frames.

    Raises:
        404: Run not found or no stack data available.
    """
    state_manager = get_state_manager()

    try:
        state, _ = await state_manager.get_run(run_id)

        # Get interruption stack from state
        # The state may come from the simple RunStateManager (dict-based)
        # or from RunState dataclass serialization
        raw_stack = state.get("interruption_stack", [])

        frames: List[InterruptionFrameResponse] = []
        detours: List[Dict[str, Any]] = []

        for idx, frame_data in enumerate(raw_stack):
            # Handle both dict format (from JSON) and dataclass format
            if isinstance(frame_data, dict):
                reason = frame_data.get("reason", "")
                interrupted_at = frame_data.get("interrupted_at", "")
                return_node = frame_data.get("return_node", "")
                current_step_index = frame_data.get("current_step_index", 0)
                total_steps = frame_data.get("total_steps", 1)
                sidequest_id = frame_data.get("sidequest_id")
                context_snapshot = frame_data.get("context_snapshot", {})
            else:
                # Assume it's an InterruptionFrame dataclass
                reason = frame_data.reason
                interrupted_at = (
                    frame_data.interrupted_at.isoformat()
                    if hasattr(frame_data.interrupted_at, "isoformat")
                    else str(frame_data.interrupted_at)
                )
                return_node = frame_data.return_node
                current_step_index = frame_data.current_step_index
                total_steps = frame_data.total_steps
                sidequest_id = frame_data.sidequest_id
                context_snapshot = frame_data.context_snapshot

            # Parse return_node to extract flow and step info
            # Format is typically "flow_key.step_id" or just "step_id"
            parts = return_node.split(".")
            interrupted_flow = parts[0] if len(parts) > 1 else state.get("flow_id")
            interrupted_step = parts[1] if len(parts) > 1 else parts[0]

            # Create structured frame response
            frame_response = InterruptionFrameResponse(
                frame_id=f"frame-{idx}",
                interrupted_flow=interrupted_flow,
                interrupted_step=interrupted_step,
                injected_flow=sidequest_id or context_snapshot.get("injected_flow"),
                reason=reason,
                started_at=interrupted_at,
                return_node=return_node,
                current_step_index=current_step_index,
                total_steps=total_steps,
                sidequest_id=sidequest_id,
            )
            frames.append(frame_response)

            # Also create simplified detour format for UI compatibility
            detour = {
                "detour_id": f"detour-{idx}",
                "from_step": f"{interrupted_flow}:{interrupted_step}",
                "to_step": sidequest_id or context_snapshot.get("injected_flow", "unknown"),
                "reason": reason,
                "detour_type": "INJECT_FLOW" if sidequest_id else "DETOUR",
                "timestamp": interrupted_at,
            }
            detours.append(detour)

        return InterruptionStackResponse(
            run_id=run_id,
            stack_depth=len(frames),
            frames=frames,
            detours=detours,
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
