from __future__ import annotations

from .agents import router as agents_router
from .flows import router as flows_router
from .health import router as health_router
from .layout import router as layout_router
from .model_policy import router as model_policy_router
from .platform import router as platform_router
from .profiles import router as profiles_router
from .runs import router as runs_router
from .station_preview import router as station_preview_router
from .tours import router as tours_router
from .validation import router as validation_router

__all__ = [
    "agents_router",
    "flows_router",
    "health_router",
    "layout_router",
    "model_policy_router",
    "platform_router",
    "profiles_router",
    "runs_router",
    "station_preview_router",
    "tours_router",
    "validation_router",
]
