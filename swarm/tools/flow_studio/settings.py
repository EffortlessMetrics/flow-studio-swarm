from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class FlowStudioSettings:
    strict_ui_assets: bool = False

    @classmethod
    def from_env(cls) -> "FlowStudioSettings":
        return cls(strict_ui_assets=os.getenv("FLOW_STUDIO_STRICT_UI_ASSETS", "0") == "1")
