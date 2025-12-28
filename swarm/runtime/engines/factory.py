"""
factory.py - Step engine factory functions.

Provides centralized engine instantiation based on configuration.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from swarm.config.runtime_config import get_engine_mode, get_engine_provider

from .base import StepEngine
from .gemini import GeminiStepEngine
from .claude import ClaudeStepEngine


def get_step_engine(
    engine_id: str,
    repo_root: Path,
    mode: Optional[str] = None,
) -> StepEngine:
    """Get a step engine by ID with optional mode override.

    This factory function provides a centralized way to instantiate engines
    based on configuration from runtime.yaml and environment variables.

    Engine IDs:
    - "gemini-step" or "gemini": GeminiStepEngine
    - "claude-step" or "claude": ClaudeStepEngine

    Args:
        engine_id: Engine identifier ("gemini-step", "claude-step", etc.)
        repo_root: Repository root path.
        mode: Optional mode override ("stub", "sdk", "cli").
              If None, reads from config/environment.

    Returns:
        Configured StepEngine instance.

    Raises:
        ValueError: If engine_id is not recognized.

    Example:
        >>> engine = get_step_engine("claude-step", Path.cwd(), mode="cli")
        >>> result, events = engine.run_step(ctx)
    """
    engine_id_lower = engine_id.lower()

    if engine_id_lower in ("gemini-step", "gemini"):
        return GeminiStepEngine(repo_root)

    if engine_id_lower in ("claude-step", "claude"):
        return ClaudeStepEngine(repo_root, mode=mode)

    raise ValueError(
        f"Unknown engine ID: {engine_id}. "
        f"Valid options: gemini-step, claude-step"
    )


def list_available_engines() -> List[Dict[str, Any]]:
    """List available step engines with their configuration.

    Returns:
        List of dicts with engine metadata:
        - id: Engine identifier
        - label: Human-readable label
        - modes: Available modes for this engine
        - default_mode: Default mode from config
        - provider: Provider name
    """
    return [
        {
            "id": "gemini-step",
            "label": "Gemini CLI",
            "modes": ["stub", "cli"],
            "default_mode": get_engine_mode("gemini"),
            "provider": "gemini",
        },
        {
            "id": "claude-step",
            "label": "Claude Agent SDK/CLI",
            "modes": ["stub", "sdk", "cli"],
            "default_mode": get_engine_mode("claude"),
            "provider": get_engine_provider("claude"),
        },
    ]
