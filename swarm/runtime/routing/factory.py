"""Router factory helpers."""

from __future__ import annotations

import os
from typing import Any, Optional, Union

from .graph_router import SmartRouter
from .step_router import StepRouter


def get_router(
    mode: Optional[str] = None,
    llm_tiebreaker: Optional[Any] = None,
) -> Union[SmartRouter, StepRouter]:
    """Select a router implementation based on config."""
    if mode is None:
        mode = os.environ.get("SWARM_ROUTER_MODE", "step")

    normalized = mode.strip().lower()
    if normalized in ("step", "stepwise", "wp4"):
        return StepRouter(llm_tiebreaker=llm_tiebreaker)
    if normalized in ("graph", "smart", "legacy"):
        return SmartRouter(llm_tiebreaker=llm_tiebreaker)

    raise ValueError(f"Unknown router mode: {mode}")
