from __future__ import annotations

from fastapi import Request

from .state import FlowStudioState


def get_state(request: Request) -> FlowStudioState:
    return request.app.state.flow_studio
