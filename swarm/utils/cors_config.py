import os
from typing import List


def get_allowed_origins() -> List[str]:
    """
    Get allowed origins for CORS configuration.
    Defaults to localhost on ports 5000 and 5001.
    Can be overridden by SWARM_ALLOWED_ORIGINS environment variable (comma-separated).
    """
    env_origins = os.getenv("SWARM_ALLOWED_ORIGINS")
    if env_origins is not None:
        return [origin.strip() for origin in env_origins.split(",") if origin.strip()]

    return [
        "http://localhost:5000",
        "http://localhost:5001",
        "http://127.0.0.1:5000",
        "http://127.0.0.1:5001",
    ]
