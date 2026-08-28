"""
backends - Run execution backends.

This package defines the RunBackend interface and the concrete backends that
execute Swarm flows. It was split out of the former ``backends.py`` module
along public backend seams (see #1445); the import surface is unchanged.

Package structure:
    base.py            - RunBackend abstract interface
    harness.py         - ClaudeHarnessBackend, AgentSDKBackend
    gemini_cli.py      - GeminiCliBackend (process/thread lifecycle)
    gemini_support.py  - Pure prompt/command/event helpers for Gemini CLI
    stepwise_gemini.py - GeminiStepwiseBackend
    stepwise_claude.py - ClaudeStepwiseBackend
    registry.py        - Canonical backend registry and lookup helpers

Usage:
    from swarm.runtime.backends import ClaudeHarnessBackend
    backend = ClaudeHarnessBackend()
    run_id = backend.start(spec)
    summary = backend.get_summary(run_id)
"""

from .base import RunBackend
from .gemini_cli import GeminiCliBackend
from .harness import AgentSDKBackend, ClaudeHarnessBackend
from .registry import _BACKEND_REGISTRY, get_backend, list_backends
from .stepwise_claude import ClaudeStepwiseBackend
from .stepwise_gemini import GeminiStepwiseBackend

__all__ = [
    "RunBackend",
    "ClaudeHarnessBackend",
    "AgentSDKBackend",
    "GeminiCliBackend",
    "GeminiStepwiseBackend",
    "ClaudeStepwiseBackend",
    "get_backend",
    "list_backends",
    "_BACKEND_REGISTRY",
]
