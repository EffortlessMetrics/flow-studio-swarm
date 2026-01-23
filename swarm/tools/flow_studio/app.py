from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import (
    agents_router,
    flows_router,
    health_router,
    layout_router,
    model_policy_router,
    platform_router,
    profiles_router,
    runs_router,
    station_preview_router,
    tours_router,
    validation_router,
)
from .settings import FlowStudioSettings
from .state import create_state
from .ui.assets import check_ui_assets, mount_static


def create_app() -> FastAPI:
    app = FastAPI(
        title="Flow Studio API",
        description="Interactive visualization of swarm flows, steps, agents, and artifacts",
        version="2.0.0",
    )

    # Define default allowed origins (localhost for development)
    default_origins = [
        "http://localhost:5000",
        "http://localhost:5001",
        "http://127.0.0.1:5000",
        "http://127.0.0.1:5001",
    ]

    # Get extra allowed origins from environment
    env_origins = os.environ.get("SWARM_ALLOWED_ORIGINS", "").split(",")
    extra_origins = [origin.strip() for origin in env_origins if origin.strip()]

    # Combine and deduplicate
    allowed_origins = list(set(default_origins + extra_origins))

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    repo_root = Path(__file__).resolve().parents[3]
    settings = FlowStudioSettings.from_env()

    state = create_state(repo_root)
    app.state.flow_studio = state
    app.state.fs = state  # Compat alias; delete later.

    app.include_router(health_router)
    app.include_router(profiles_router)
    app.include_router(model_policy_router)
    app.include_router(flows_router)
    app.include_router(agents_router)
    app.include_router(runs_router)
    app.include_router(platform_router)
    app.include_router(validation_router)
    app.include_router(tours_router)
    app.include_router(layout_router)
    app.include_router(station_preview_router)

    ui_dir = repo_root / "swarm" / "tools" / "flow_studio_ui"
    check_ui_assets(ui_dir, settings.strict_ui_assets)
    mount_static(app, ui_dir)

    return app
