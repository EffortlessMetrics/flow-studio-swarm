"""
Flow Studio API - FastAPI REST API for SpecManager functionality.

This module exposes the spec system (flows, templates, validation, compilation)
to the TypeScript frontend via a FastAPI REST API.

Note: Although the original design mentioned Flask, the codebase standardizes
on FastAPI. This implementation follows FastAPI patterns for consistency.

IMPORTANT: To avoid import side effects, the app instance is NOT created at
import time. Use one of these patterns:

    # For ASGI servers (recommended):
    uvicorn swarm.api.asgi:app --port 5001

    # For programmatic access to the app:
    from swarm.api.asgi import app

    # For just the factory (no app creation):
    from swarm.api import create_app
    app = create_app()

New API (v2.0) - Modular Routes:
    Spec Endpoints (from routes/specs.py):
        GET    /api/specs/templates          - List templates (for palette)
        GET    /api/specs/templates/{id}     - Get template
        GET    /api/specs/flows              - List flows
        GET    /api/specs/flows/{id}         - Get merged flow
        PATCH  /api/specs/flows/{id}         - Update flow (requires If-Match)
        POST   /api/specs/flows/{id}/validate - Validate flow spec
        POST   /api/specs/flows/{id}/compile  - Compile flow

    Run Control Endpoints (from routes/runs.py):
        POST   /api/runs                     - Start new run
        GET    /api/runs                     - List runs
        GET    /api/runs/{id}                - Get run state
        POST   /api/runs/{id}/pause          - Pause run
        POST   /api/runs/{id}/resume         - Resume run
        POST   /api/runs/{id}/inject         - Inject node into run
        POST   /api/runs/{id}/interrupt      - Interrupt with detour
        DELETE /api/runs/{id}                - Cancel run

    SSE Event Streaming (from routes/events.py):
        GET    /api/runs/{id}/events         - Stream run events

    Health:
        GET    /api/health                   - Health check

Legacy API (v1.0) - Backward Compatible:
    GET  /api/spec/flows              - List all flows
    GET  /api/spec/flows/<flow_id>    - Get flow graph (with ETag)
    PATCH /api/spec/flows/<flow_id>   - Update flow (JSON Patch, If-Match)
    GET  /api/spec/templates          - List all templates
    GET  /api/spec/templates/<id>     - Get template details
    POST /api/spec/validate           - Dry-run validation
    POST /api/spec/compile            - Preview PromptPlan
    GET  /api/runs                    - List runs
    GET  /api/runs/<run_id>/state     - Get run state
    GET  /api/runs/<run_id>/events    - SSE event stream
"""

# Import factory and manager without triggering app creation
from .server import SpecManager, create_app, get_spec_manager

# Base exports (always available, no side effects)
__all__ = [
    "create_app",
    "SpecManager",
    "get_spec_manager",
]

# Expose routers for custom integration (no app creation side effects)
try:
    from .routes import events_router, runs_router, specs_router

    __all__.extend(["specs_router", "runs_router", "events_router"])
except ImportError:
    pass


def get_app():
    """Get the app instance (creates on first call).

    This is a lazy accessor that avoids import-time app creation.
    For direct access to the singleton app, use: from swarm.api.asgi import app
    """
    from .asgi import app

    return app
