"""
ASGI entrypoint for Flow Studio API.

This module creates the FastAPI app instance for use with ASGI servers.
Import the app from this module for uvicorn or other ASGI servers:

    uvicorn swarm.api.asgi:app --port 5001

By keeping app creation in a dedicated entrypoint:
- Importing swarm.api.server doesn't trigger app construction
- Importing swarm.api.services doesn't trigger router wiring
- Unit tests can import routers/services in isolation
"""

from .server import create_app

# Create the app instance for ASGI servers
app = create_app()
