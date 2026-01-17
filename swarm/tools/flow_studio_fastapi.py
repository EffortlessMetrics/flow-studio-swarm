#!/usr/bin/env python3
"""
Flow Studio - FastAPI Implementation (shim).

Compatibility entrypoint for uvicorn and existing imports.
"""

from __future__ import annotations

try:
    from swarm.runtime.service import RunService
except ImportError:  # pragma: no cover - optional dependency
    RunService = None

from swarm.tools.flow_studio.app import create_app as create_fastapi_app
from swarm.tools.flow_studio.app import create_app

app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=5000)
