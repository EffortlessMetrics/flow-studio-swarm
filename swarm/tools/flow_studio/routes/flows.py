from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from ..deps import get_state
from ..services.search import build_artifact_graph, search
from ..state import FlowStudioState

try:
    from swarm.flowstudio import schema
except ImportError:
    schema = None

router = APIRouter()


@router.get("/api/flows", response_model=schema.FlowsListResponse if schema else None)
async def api_flows(state: FlowStudioState = Depends(get_state)) -> dict[str, Any]:
    if not state.core:
        return {"flows": []}

    flows = state.core.list_flows()
    return {
        "flows": [
            {
                "key": f.key,
                "title": f.title,
                "description": f.description,
                "step_count": f.step_count,
            }
            for f in flows
        ]
    }


@router.get("/api/graph/{flow_key}", response_model=schema.GraphPayload if schema else None)
async def api_graph(flow_key: str, state: FlowStudioState = Depends(get_state)):
    if not state.core:
        return JSONResponse({"error": "Flow Studio core not available"}, status_code=503)

    try:
        graph = state.core.get_flow_graph(flow_key)
        return graph.to_dict()
    except KeyError:
        available = sorted([f.key for f in state.core.list_flows()]) if state.core else []
        return JSONResponse(
            {
                "error": f"Flow '{flow_key}' not found",
                "available_flows": available,
                "hint": f"Available flows: {', '.join(available)}" if available else "No flows loaded",
            },
            status_code=404,
        )


@router.get("/api/flows/{flow_key}", response_model=schema.FlowDetail if schema else None)
async def api_flow_detail(flow_key: str, state: FlowStudioState = Depends(get_state)):
    if flow_key not in state.flows_cache:
        available = sorted(state.flows_cache.keys())
        return JSONResponse(
            {
                "error": f"Flow '{flow_key}' not found",
                "available_flows": available,
                "hint": f"Available flows: {', '.join(available)}" if available else "No flows loaded",
            },
            status_code=404,
        )

    flow = state.flows_cache[flow_key]
    steps = []
    used_agents: dict[str, bool] = {}

    for step in flow.get("steps", []):
        steps.append(
            {
                "id": step["id"],
                "title": step["title"],
                "role": step["role"],
                "agents": step["agents"],
            }
        )
        for agent_key in step.get("agents", []):
            used_agents[agent_key] = True

    agents: dict[str, Any] = {}
    for agent_key in sorted(used_agents.keys()):
        agent = state.agents_cache.get(agent_key)
        if agent:
            agents[agent_key] = agent
        else:
            agents[agent_key] = {
                "key": agent_key,
                "category": "unknown",
                "color": "#9ca3af",
                "model": "inherit",
                "short_role": "",
            }

    return {
        "flow": {
            "key": flow["key"],
            "title": flow["title"],
            "description": flow["description"],
        },
        "steps": steps,
        "agents": agents,
    }


@router.get(
    "/api/graph/{flow_key}/artifacts",
    response_model=schema.GraphPayload if schema else None,
)
async def api_graph_artifacts(
    flow_key: str,
    run_id: str = Query(None, description="Optional run ID to overlay artifact status"),
    state: FlowStudioState = Depends(get_state),
):
    if flow_key not in state.flows_cache:
        available = sorted(state.flows_cache.keys())
        return JSONResponse(
            {
                "error": f"Flow '{flow_key}' not found",
                "available_flows": available,
                "hint": f"Available flows: {', '.join(available)}" if available else "No flows loaded",
            },
            status_code=404,
        )

    flow = state.flows_cache[flow_key]
    return build_artifact_graph(
        flow_key=flow_key,
        flow=flow,
        repo_root=state.repo_root,
        run_inspector=state.run_inspector,
        run_id=run_id,
    )


@router.get("/api/search", response_model=schema.SearchResponse if schema else None)
async def api_search(q: str = Query("", description="Search query"), state: FlowStudioState = Depends(get_state)):
    return search(state.flows_cache, state.agents_cache, q, state.agent_flow_index)
