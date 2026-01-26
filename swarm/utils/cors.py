"""
cors.py - CORS configuration utility.

This module provides a consistent way to configure CORS origins across
the Flow Studio API and UI servers.
"""

import os
from typing import List


def get_cors_origins() -> List[str]:
    """Get the list of allowed CORS origins.

    Reads from SWARM_ALLOWED_ORIGINS environment variable.
    If not set, defaults to localhost on ports 5000 and 5001.

    Returns:
        List of allowed origins.
    """
    env_origins = os.getenv("SWARM_ALLOWED_ORIGINS")

    if env_origins is not None:
        # If set but empty, return empty list
        if not env_origins.strip():
            return []
        # If explicitly set to '*', return as is
        if env_origins.strip() == "*":
            return ["*"]
        # Otherwise split by comma
        return [origin.strip() for origin in env_origins.split(",") if origin.strip()]

    # Default permissive local development defaults
    return [
        "http://localhost:5000",
        "http://127.0.0.1:5000",
        "http://localhost:5001",
        "http://127.0.0.1:5001",
    ]
