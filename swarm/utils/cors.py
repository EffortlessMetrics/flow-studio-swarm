import os
from typing import List


def get_cors_origins() -> List[str]:
    """
    Get allowed CORS origins.

    Defaults to localhost:5000, localhost:5001, and 127.0.0.1 variants.
    Can be overridden by SWARM_ALLOWED_ORIGINS environment variable
    (comma-separated list).

    If SWARM_ALLOWED_ORIGINS is empty string, returns empty list (disables CORS).
    If SWARM_ALLOWED_ORIGINS is "*", returns ["*"] (allows all).
    """
    env_origins = os.getenv("SWARM_ALLOWED_ORIGINS")

    if env_origins is None:
        return [
            "http://localhost:5000",
            "http://localhost:5001",
            "http://127.0.0.1:5000",
            "http://127.0.0.1:5001",
        ]

    if env_origins.strip() == "":
        return []

    return [origin.strip() for origin in env_origins.split(",") if origin.strip()]
