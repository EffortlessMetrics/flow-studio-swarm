"""
FastAPI REST API server for SpecManager functionality.

Exposes the spec system (flows, templates, validation, compilation) to the
TypeScript frontend.

Note: Although the original request specified Flask, the codebase standardizes
on FastAPI. This implementation follows FastAPI patterns to match existing code
in swarm/tools/flow_studio_fastapi.py.

Usage:
    # Run standalone
    python -m swarm.api.server

    # Or via factory
    from swarm.api import create_app, SpecManager
    app = create_app()
    uvicorn.run(app, port=5001)

API Structure:
    /api/specs/           - Template and flow graph endpoints (from routes/specs.py)
    /api/runs/            - Run control endpoints (from routes/runs.py)
    /api/runs/{id}/events - SSE streaming (from routes/events.py)
    /api/spec/            - Legacy endpoints (inline, for backward compatibility)
    /api/health           - Health check
"""

from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Import SpecManager from services
from .services.spec_manager import SpecManager, get_spec_manager, set_spec_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# Pydantic Models for Request/Response
# =============================================================================


class FlowSummary(BaseModel):
    """Flow summary for list endpoint."""

    id: str
    title: str
    flow_number: Optional[int] = None
    version: int = 1
    description: str = ""


class FlowListResponse(BaseModel):
    """Response for list flows endpoint."""

    flows: List[FlowSummary]


class TemplateSummary(BaseModel):
    """Template summary for list endpoint."""

    id: str
    title: str
    station_id: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = []
    description: str = ""


class TemplateListResponse(BaseModel):
    """Response for list templates endpoint."""

    templates: List[TemplateSummary]


class ValidationRequest(BaseModel):
    """Request for validation endpoint."""

    id: Optional[str] = None
    version: Optional[int] = None
    title: Optional[str] = None
    nodes: Optional[List[Dict[str, Any]]] = None
    edges: Optional[List[Dict[str, Any]]] = None


class ValidationResponse(BaseModel):
    """Response for validation endpoint."""

    valid: bool
    errors: List[str]


class CompileRequest(BaseModel):
    """Request for compile endpoint."""

    flow_id: str
    step_id: str
    run_id: Optional[str] = None


class CompileResponse(BaseModel):
    """Response for compile endpoint."""

    prompt_plan: Dict[str, Any]


class RunSummary(BaseModel):
    """Run summary for list endpoint."""

    run_id: str
    flow_key: Optional[str] = None
    status: Optional[str] = None
    timestamp: Optional[str] = None


class RunListResponse(BaseModel):
    """Response for list runs endpoint."""

    runs: List[RunSummary]


class DBHealthInfo(BaseModel):
    """Database health information."""

    healthy: bool = False
    projection_version: int = 0
    db_exists: bool = False
    rebuild_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    last_check: Optional[str] = None
    last_rebuild: Optional[str] = None


class TailerHealthInfo(BaseModel):
    """RunTailer health information."""

    enabled: bool = False
    active_runs: int = 0
    total_events_ingested: int = 0
    last_ingest_at: Optional[str] = None
    error: Optional[str] = None


class TailerIngestResponse(BaseModel):
    """Response for manual tailer ingest endpoint."""

    run_id: str
    events_ingested: int


class HealthResponse(BaseModel):
    """Response for health check endpoint."""

    status: str
    timestamp: str
    repo_root: str
    db: Optional[DBHealthInfo] = None
    tailer: Optional[TailerHealthInfo] = None


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    message: str
    details: Dict[str, Any] = {}


# =============================================================================
# FastAPI Application Factory
# =============================================================================


def create_app(
    repo_root: Optional[Path] = None,
    enable_cors: bool = True,
) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        repo_root: Repository root path for SpecManager.
        enable_cors: Whether to enable CORS middleware.

    Returns:
        Configured FastAPI application.
    """
    # Initialize the global SpecManager instance
    set_spec_manager(SpecManager(repo_root))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Application lifespan manager.

        On startup:
        - Initialize the resilient stats database
        - Check DB schema version and rebuild from events.jsonl if needed
        - Initialize RunTailer for incremental event ingestion
        - Start background task to watch active runs

        On shutdown:
        - Cancel the tailer background task
        - Close the database connection
        """
        logger.info("Spec API server starting...")

        # Initialize resilient database with auto-rebuild
        db_available = False
        try:
            from swarm.runtime.resilient_db import close_resilient_db, get_resilient_db

            db = get_resilient_db()
            health = db.health
            logger.info(
                "Resilient DB initialized: healthy=%s, projection_version=%d, rebuild_count=%d",
                health.healthy,
                health.projection_version,
                health.rebuild_count,
            )
            if health.last_error:
                logger.warning("DB initialization had error: %s", health.last_error)
            db_available = True
        except Exception as e:
            logger.warning("Could not initialize resilient DB (non-fatal): %s", e)

        # Initialize RunTailer for incremental event ingestion
        tailer_task: Optional[asyncio.Task] = None
        tailer_state: Dict[str, Any] = {
            "enabled": False,
            "total_events_ingested": 0,
            "last_ingest_at": None,
            "error": None,
        }

        if db_available:
            try:
                from swarm.runtime.db import get_stats_db
                from swarm.runtime.run_tailer import RunTailer

                # Get runs directory from spec manager
                spec_mgr = get_spec_manager()
                runs_dir = spec_mgr.runs_root

                # Create tailer with the stats database
                stats_db = get_stats_db()
                tailer = RunTailer(db=stats_db, runs_dir=runs_dir)

                # Store tailer in app state for access by endpoints
                app.state.tailer = tailer
                app.state.tailer_state = tailer_state

                async def watch_active_runs():
                    """Background task to watch active runs for new events."""
                    try:
                        async for results in tailer.watch_active_runs(poll_interval_ms=1000):
                            total_ingested = sum(results.values())
                            tailer_state["total_events_ingested"] += total_ingested
                            tailer_state["last_ingest_at"] = datetime.now(
                                timezone.utc
                            ).isoformat()
                            logger.debug(
                                "Tailer ingested %d events from %d runs",
                                total_ingested,
                                len(results),
                            )
                    except asyncio.CancelledError:
                        logger.info("RunTailer watch task cancelled")
                        raise
                    except Exception as e:
                        tailer_state["error"] = str(e)
                        logger.error("RunTailer watch task error: %s", e)

                # Start background tailing task
                tailer_task = asyncio.create_task(watch_active_runs())
                tailer_state["enabled"] = True
                logger.info("RunTailer initialized and watching for events")

            except ImportError as e:
                logger.warning("Could not initialize RunTailer (missing module): %s", e)
                tailer_state["error"] = f"Import error: {e}"
            except Exception as e:
                logger.warning("Could not initialize RunTailer (non-fatal): %s", e)
                tailer_state["error"] = str(e)
        else:
            tailer_state["error"] = "Database not available"
            logger.info("RunTailer disabled (database not available)")

        yield

        logger.info("Spec API server shutting down...")

        # Cancel the tailer background task
        if tailer_task is not None:
            tailer_task.cancel()
            try:
                await tailer_task
            except asyncio.CancelledError:
                pass
            logger.info("RunTailer task stopped")

        # Close the resilient database
        try:
            close_resilient_db()
            logger.info("Resilient DB closed")
        except Exception as e:
            logger.warning("Error closing resilient DB: %s", e)

    app = FastAPI(
        title="Flow Studio API",
        description="REST API for SpecManager functionality - exposes flows, templates, validation, and compilation to the TypeScript frontend.",
        version="2.0.0",
        lifespan=lifespan,
    )

    # Add CORS middleware
    if enable_cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["*"],
            expose_headers=["ETag", "If-Match", "If-None-Match"],
        )

    # -------------------------------------------------------------------------
    # Include Modular Routers
    # -------------------------------------------------------------------------
    # These routers provide the new API structure with full run control
    try:
        from .routes import (
            boundary_router,
            compile_router,
            db_router,
            events_router,
            evolution_router,
            facts_router,
            preview_router,
            runs_router,
            settings_router,
            specs_router,
            wisdom_router,
        )

        app.include_router(specs_router, prefix="/api")
        app.include_router(runs_router, prefix="/api")
        app.include_router(events_router, prefix="/api")
        app.include_router(wisdom_router, prefix="/api")
        app.include_router(compile_router, prefix="/api")
        app.include_router(facts_router, prefix="/api")
        app.include_router(evolution_router, prefix="/api")
        app.include_router(boundary_router, prefix="/api")
        app.include_router(db_router, prefix="/api")
        app.include_router(settings_router, prefix="/api")
        app.include_router(preview_router, prefix="/api")
        logger.info("Loaded modular API routers")
    except ImportError as e:
        logger.warning("Could not load modular routers: %s", e)

    # -------------------------------------------------------------------------
    # Request Logging Middleware
    # -------------------------------------------------------------------------

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time
        logger.info(
            "%s %s %s %.3fs",
            request.method,
            request.url.path,
            response.status_code,
            duration,
        )
        return response

    # -------------------------------------------------------------------------
    # Flow Graph Endpoints
    # -------------------------------------------------------------------------

    @app.get("/api/spec/flows", response_model=FlowListResponse, operation_id="legacy_list_flows")
    async def list_flows():
        """List all available flow graphs."""
        flows = get_spec_manager().list_flows()
        return FlowListResponse(flows=[FlowSummary(**f) for f in flows])

    @app.get("/api/spec/flows/{flow_id}", operation_id="legacy_get_flow")
    async def get_flow(
        flow_id: str,
        if_none_match: Optional[str] = Header(None),
    ):
        """Get a flow graph by ID."""
        try:
            flow_data, etag = get_spec_manager().get_flow(flow_id)

            # Check If-None-Match for caching (strip quotes from ETag)
            if if_none_match and if_none_match.strip('"') == etag:
                return Response(status_code=304)

            return JSONResponse(
                content=flow_data,
                headers={"ETag": f'"{etag}"'},
            )

        except FileNotFoundError:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "spec_not_found",
                    "message": f"Flow graph '{flow_id}' not found",
                    "details": {},
                },
            )

    @app.patch("/api/spec/flows/{flow_id}", operation_id="legacy_update_flow")
    async def update_flow(
        flow_id: str,
        patch_ops: List[Dict[str, Any]],
        if_match: str = Header(..., description="ETag for optimistic concurrency"),
    ):
        """Update a flow graph with JSON Patch operations."""
        try:
            updated_data, new_etag = get_spec_manager().update_flow(flow_id, patch_ops, if_match)

            return JSONResponse(
                content=updated_data,
                headers={"ETag": new_etag},
            )

        except FileNotFoundError:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "spec_not_found",
                    "message": f"Flow graph '{flow_id}' not found",
                    "details": {},
                },
            )
        except ValueError as e:
            if "ETag mismatch" in str(e):
                raise HTTPException(
                    status_code=412,
                    detail={
                        "error": "etag_mismatch",
                        "message": str(e),
                        "details": {},
                    },
                )
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "validation_error",
                    "message": str(e),
                    "details": {},
                },
            )

    # -------------------------------------------------------------------------
    # Template Endpoints
    # -------------------------------------------------------------------------

    @app.get("/api/spec/templates", response_model=TemplateListResponse, operation_id="legacy_list_templates")
    async def list_templates():
        """List all available step templates."""
        templates = get_spec_manager().list_templates()
        return TemplateListResponse(templates=[TemplateSummary(**t) for t in templates])

    @app.get("/api/spec/templates/{template_id}", operation_id="legacy_get_template")
    async def get_template(
        template_id: str,
        if_none_match: Optional[str] = Header(None),
    ):
        """Get a template by ID."""
        try:
            template_data, etag = get_spec_manager().get_template(template_id)

            # Check If-None-Match for caching (strip quotes from ETag)
            if if_none_match and if_none_match.strip('"') == etag:
                return Response(status_code=304)

            return JSONResponse(
                content=template_data,
                headers={"ETag": f'"{etag}"'},
            )

        except FileNotFoundError:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "template_not_found",
                    "message": f"Template '{template_id}' not found",
                    "details": {},
                },
            )

    # -------------------------------------------------------------------------
    # Validation / Compilation Endpoints
    # -------------------------------------------------------------------------

    @app.post("/api/spec/validate", response_model=ValidationResponse, operation_id="legacy_validate_spec")
    async def validate_spec(request: ValidationRequest):
        """Validate a flow spec without saving."""
        data = request.model_dump(exclude_none=True)
        errors = get_spec_manager().validate_flow(data)
        return ValidationResponse(valid=len(errors) == 0, errors=errors)

    @app.post("/api/spec/compile", response_model=CompileResponse, operation_id="legacy_compile_spec")
    async def compile_spec(request: CompileRequest):
        """Preview PromptPlan compilation."""
        try:
            prompt_plan = get_spec_manager().compile_prompt_plan(
                flow_id=request.flow_id,
                step_id=request.step_id,
                run_id=request.run_id,
            )
            return CompileResponse(prompt_plan=prompt_plan)

        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "compilation_error",
                    "message": str(e),
                    "details": {},
                },
            )

    # -------------------------------------------------------------------------
    # Health Check
    # -------------------------------------------------------------------------

    @app.get("/api/health", response_model=HealthResponse, operation_id="api_health_check")
    async def health_check(request: Request):
        """Health check endpoint.

        Returns overall API health including database and tailer status.
        The API is considered healthy even if the DB or tailer has issues,
        since these operations fail gracefully.
        """
        # Get DB health info
        db_info = None
        try:
            from swarm.runtime.resilient_db import check_db_health

            health = check_db_health()
            db_info = DBHealthInfo(
                healthy=health.healthy,
                projection_version=health.projection_version,
                db_exists=health.db_exists,
                rebuild_count=health.rebuild_count,
                error_count=health.error_count,
                last_error=health.last_error,
                last_check=health.last_check.isoformat() if health.last_check else None,
                last_rebuild=health.last_rebuild.isoformat() if health.last_rebuild else None,
            )
        except Exception as e:
            logger.warning("Could not get DB health: %s", e)
            db_info = DBHealthInfo(healthy=False, last_error=str(e))

        # Get tailer health info
        tailer_info = None
        try:
            tailer_state = getattr(request.app.state, "tailer_state", None)
            if tailer_state:
                # Count active runs from the tailer if available
                active_runs = 0
                tailer = getattr(request.app.state, "tailer", None)
                if tailer:
                    try:
                        from swarm.runtime.storage import list_runs

                        active_runs = len(list(list_runs(tailer._runs_dir)))
                    except Exception:
                        pass

                tailer_info = TailerHealthInfo(
                    enabled=tailer_state.get("enabled", False),
                    active_runs=active_runs,
                    total_events_ingested=tailer_state.get("total_events_ingested", 0),
                    last_ingest_at=tailer_state.get("last_ingest_at"),
                    error=tailer_state.get("error"),
                )
            else:
                tailer_info = TailerHealthInfo(enabled=False, error="Tailer state not available")
        except Exception as e:
            logger.warning("Could not get tailer health: %s", e)
            tailer_info = TailerHealthInfo(enabled=False, error=str(e))

        return HealthResponse(
            status="healthy",
            timestamp=datetime.now(timezone.utc).isoformat(),
            repo_root=str(get_spec_manager().repo_root),
            db=db_info,
            tailer=tailer_info,
        )

    # -------------------------------------------------------------------------
    # RunTailer Endpoints
    # -------------------------------------------------------------------------

    @app.get("/api/tailer/health", response_model=TailerHealthInfo, operation_id="tailer_health_check")
    async def tailer_health(request: Request):
        """Check RunTailer health.

        Returns detailed information about the RunTailer status including
        whether it's enabled, active run count, and ingestion statistics.
        """
        tailer_state = getattr(request.app.state, "tailer_state", None)

        if not tailer_state:
            return TailerHealthInfo(enabled=False, error="Tailer not initialized")

        # Count active runs
        active_runs = 0
        tailer = getattr(request.app.state, "tailer", None)
        if tailer:
            try:
                from swarm.runtime.storage import list_runs

                active_runs = len(list(list_runs(tailer._runs_dir)))
            except Exception:
                pass

        return TailerHealthInfo(
            enabled=tailer_state.get("enabled", False),
            active_runs=active_runs,
            total_events_ingested=tailer_state.get("total_events_ingested", 0),
            last_ingest_at=tailer_state.get("last_ingest_at"),
            error=tailer_state.get("error"),
        )

    @app.post("/api/tailer/ingest/{run_id}", response_model=TailerIngestResponse, operation_id="tailer_trigger_ingest")
    async def trigger_ingest(run_id: str, request: Request):
        """Manually trigger ingestion for a specific run.

        This endpoint allows explicit ingestion of events from a run's
        events.jsonl file, useful for testing or forcing immediate updates.

        Args:
            run_id: The run identifier to ingest events from.

        Returns:
            The run_id and count of events ingested.

        Raises:
            HTTPException: If tailer is not available or ingestion fails.
        """
        tailer = getattr(request.app.state, "tailer", None)
        tailer_state = getattr(request.app.state, "tailer_state", None)

        if not tailer:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "tailer_unavailable",
                    "message": "RunTailer is not available",
                    "details": {},
                },
            )

        try:
            events_ingested = tailer.tail_run(run_id)

            # Update state tracking
            if tailer_state and events_ingested > 0:
                tailer_state["total_events_ingested"] += events_ingested
                tailer_state["last_ingest_at"] = datetime.now(timezone.utc).isoformat()

            return TailerIngestResponse(run_id=run_id, events_ingested=events_ingested)

        except Exception as e:
            logger.error("Failed to ingest events for run %s: %s", run_id, e)
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "ingestion_failed",
                    "message": f"Failed to ingest events: {e}",
                    "details": {"run_id": run_id},
                },
            )

    return app


# NOTE: Module-level app creation removed to avoid import side effects.
# For ASGI servers, use: uvicorn swarm.api.asgi:app
# For programmatic access, use: from swarm.api.asgi import app


# =============================================================================
# Main Entry Point
# =============================================================================


def main():
    """Run the API server."""
    import argparse

    import uvicorn

    parser = argparse.ArgumentParser(description="Spec API Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=5001, help="Port to bind to")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--no-cors", action="store_true", help="Disable CORS")
    args = parser.parse_args()

    app = create_app(enable_cors=not args.no_cors)

    print(f"Starting Flow Studio API server at http://{args.host}:{args.port}")
    print("\nNew API Endpoints (v2.0):")
    print("  Specs:")
    print("    GET    /api/specs/templates          - List templates (for palette)")
    print("    GET    /api/specs/templates/{id}     - Get template")
    print("    GET    /api/specs/flows              - List flows")
    print("    GET    /api/specs/flows/{id}         - Get merged flow")
    print("    PATCH  /api/specs/flows/{id}         - Update flow (requires If-Match)")
    print("    POST   /api/specs/flows/{id}/validate - Validate flow spec")
    print("    POST   /api/specs/flows/{id}/compile  - Compile flow")
    print("  Compile Preview:")
    print("    POST   /api/compile/preview          - Preview compiled prompt (NEW)")
    print("    GET    /api/compile/stations         - List available stations (NEW)")
    print("    GET    /api/compile/stations/{id}    - Get station details (NEW)")
    print("    POST   /api/compile/validate         - Validate station/step (NEW)")
    print("  Runs:")
    print("    POST   /api/runs                     - Start new run")
    print("    GET    /api/runs                     - List runs")
    print("    GET    /api/runs/{id}                - Get run state")
    print("    POST   /api/runs/{id}/pause          - Pause run")
    print("    POST   /api/runs/{id}/resume         - Resume run")
    print("    POST   /api/runs/{id}/inject         - Inject node into run")
    print("    POST   /api/runs/{id}/interrupt      - Interrupt with detour")
    print("    DELETE /api/runs/{id}                - Cancel run")
    print("    GET    /api/runs/{id}/events         - SSE event stream")
    print("\nLegacy API Endpoints (v1.0 - backward compatible):")
    print("    GET    /api/spec/flows               - List flows")
    print("    GET    /api/spec/flows/{id}          - Get flow")
    print("    PATCH  /api/spec/flows/{id}          - Update flow")
    print("    GET    /api/spec/templates           - List templates")
    print("    GET    /api/spec/templates/{id}      - Get template")
    print("    POST   /api/spec/validate            - Validate spec")
    print("    POST   /api/spec/compile             - Compile spec")
    print("    GET    /api/runs                     - List runs (legacy)")
    print("    GET    /api/runs/{id}/state          - Get run state (legacy)")
    print("    GET    /api/health                   - Health check")
    print("  Tailer:")
    print("    GET    /api/tailer/health            - Check RunTailer health")
    print("    POST   /api/tailer/ingest/{run_id}   - Manually trigger ingestion")
    print("  Settings:")
    print("    GET    /api/settings/model-policy    - Get model policy configuration")
    print("    POST   /api/settings/model-policy    - Update model policy")
    print("    POST   /api/settings/model-policy/reload - Force reload from disk")
    print("  Preview:")
    print("    POST   /api/preview/settings/model-policy - Preview model policy changes")
    print("    POST   /api/preview/spec/stations/{id}    - Preview station configuration")
    print("    POST   /api/preview/spec/flows/{id}/validate - Validate flow graph")

    uvicorn.run(app, host=args.host, port=args.port, reload=args.debug)


if __name__ == "__main__":
    main()
