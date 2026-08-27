"""registry - Canonical backend registry.

Single mapping from backend ID to implementation, plus the lookup helpers
used by RunService and the API execution path.
"""

from __future__ import annotations

import logging
from typing import List

from ..types import (
    BackendCapabilities,
    BackendId,
)
from .base import RunBackend
from .gemini_cli import GeminiCliBackend
from .harness import AgentSDKBackend, ClaudeHarnessBackend
from .stepwise_claude import ClaudeStepwiseBackend
from .stepwise_gemini import GeminiStepwiseBackend

logger = logging.getLogger(__name__)




# Registry of available backends
_BACKEND_REGISTRY: dict[BackendId, type[RunBackend]] = {
    "claude-harness": ClaudeHarnessBackend,
    "claude-agent-sdk": AgentSDKBackend,
    "gemini-cli": GeminiCliBackend,
    "gemini-step-orchestrator": GeminiStepwiseBackend,
    "claude-step-orchestrator": ClaudeStepwiseBackend,
}


def get_backend(backend_id: BackendId) -> RunBackend:
    """Get a backend instance by ID."""
    backend_class = _BACKEND_REGISTRY.get(backend_id)
    if not backend_class:
        raise ValueError(f"Unknown backend: {backend_id}")
    return backend_class()


def list_backends() -> List[BackendCapabilities]:
    """List capabilities of all registered backends."""
    return [get_backend(bid).capabilities() for bid in _BACKEND_REGISTRY]
