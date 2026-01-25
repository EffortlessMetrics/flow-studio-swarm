"""
CORS Configuration Utility.

Provides centralized configuration for Cross-Origin Resource Sharing (CORS)
policy. Defaults to allowing local development origins but supports override
via SWARM_ALLOWED_ORIGINS environment variable.
"""

import os
from typing import List

# Default origins allowed for local development
DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:5000",
    "http://localhost:5001",
    "http://127.0.0.1:5000",
    "http://127.0.0.1:5001",
]


def get_cors_origins() -> List[str]:
    """
    Get the list of allowed origins for CORS.

    If SWARM_ALLOWED_ORIGINS environment variable is set, it parses it as
    a comma-separated list. If set to empty string, returns empty list.
    Otherwise, returns DEFAULT_ALLOWED_ORIGINS.

    Returns:
        List of allowed origin strings.
    """
    env_origins = os.environ.get("SWARM_ALLOWED_ORIGINS")

    if env_origins is not None:
        if not env_origins.strip():
            return []
        return [origin.strip() for origin in env_origins.split(",") if origin.strip()]

    return DEFAULT_ALLOWED_ORIGINS
