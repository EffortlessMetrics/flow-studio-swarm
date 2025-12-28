"""
Spec API - FastAPI REST API for SpecManager functionality.

This module exposes the spec system (flows, templates, validation, compilation)
to the TypeScript frontend via a FastAPI REST API.

Note: Although the original design mentioned Flask, the codebase standardizes
on FastAPI. This implementation follows FastAPI patterns for consistency.

Endpoints:
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
    GET  /api/health                  - Health check
"""

from .server import create_app, SpecManager, app

__all__ = ["create_app", "SpecManager", "app"]
