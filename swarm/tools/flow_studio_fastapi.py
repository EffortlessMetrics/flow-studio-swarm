#!/usr/bin/env python3
"""
Flow Studio - FastAPI Implementation (shim).

Compatibility entrypoint for uvicorn and existing imports.
"""

from __future__ import annotations

from swarm.tools.flow_studio.app import create_app as create_fastapi_app

# Backwards-compat alias (some callers may import create_app)
create_app = create_fastapi_app

# Uvicorn entrypoint expects `app`
app = create_fastapi_app()

__all__ = ["app", "create_app", "create_fastapi_app"]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=5000)
