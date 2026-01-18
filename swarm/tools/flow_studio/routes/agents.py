from __future__ import annotations

from typing import Any, List

from fastapi import APIRouter, Depends

from ..deps import get_state
from ..state import FlowStudioState

try:
    from swarm.flowstudio import schema
except ImportError:
    schema = None

router = APIRouter()


@router.get("/api/agents", response_model=schema.AgentsListResponse if schema else None)
async def api_agents(state: FlowStudioState = Depends(get_state)):
    return {"agents": list(state.agents_cache.values())}


@router.get(
    "/api/agents/{agent_key}/usage",
    response_model=schema.AgentUsageResponse if schema else None,
)
async def api_agent_usage(agent_key: str, state: FlowStudioState = Depends(get_state)):
    usage: List[dict[str, Any]] = []

    for flow_key, flow in state.flows_cache.items():
        for step in flow.get("steps", []):
            if agent_key in step.get("agents", []):
                usage.append(
                    {
                        "flow": flow_key,
                        "flow_title": flow["title"],
                        "step": step["id"],
                        "step_title": step["title"],
                    }
                )

    return {
        "agent": agent_key,
        "usage": usage,
    }
