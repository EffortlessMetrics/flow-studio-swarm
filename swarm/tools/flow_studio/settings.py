from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class FlowStudioSettings:
    strict_ui_assets: bool = False
    allowed_origins: List[str] = field(default_factory=list)

    @classmethod
    def from_env(cls) -> "FlowStudioSettings":
        strict_ui_assets = os.getenv("FLOW_STUDIO_STRICT_UI_ASSETS", "0") == "1"

        # Default allowed origins
        origins = [
            "http://localhost:5000",
            "http://127.0.0.1:5000",
            "http://localhost:5001",
            "http://127.0.0.1:5001",
        ]

        # Add env var origins
        env_origins = os.getenv("SWARM_ALLOWED_ORIGINS", "")
        if env_origins:
            origins.extend([o.strip() for o in env_origins.split(",") if o.strip()])

        return cls(
            strict_ui_assets=strict_ui_assets,
            allowed_origins=origins,
        )
