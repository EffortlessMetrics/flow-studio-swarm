"""Query helpers for the Claude SDK integration.

This module provides functions for executing queries with the Claude SDK,
wrapping the underlying sdk.query() with consistent error handling and logging.

Usage:
    from swarm.runtime._claude_sdk.query import (
        query_with_options,
        query_simple,
    )
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, AsyncIterator, Optional, Union

from swarm.runtime._claude_sdk.options import create_high_trust_options
from swarm.runtime._claude_sdk.sdk_import import get_sdk_module


async def query_with_options(
    prompt: str,
    options: Any,
) -> AsyncIterator[Any]:
    """Execute a query with the provided options.

    This is a thin wrapper around sdk.query() that provides:
    - Consistent error handling
    - Logging
    - Type hints

    Args:
        prompt: The prompt to send to the SDK.
        options: ClaudeCodeOptions instance.

    Yields:
        SDK events from the query response.

    Raises:
        ImportError: If SDK is not available.
    """
    sdk = get_sdk_module()

    async for event in sdk.query(prompt=prompt, options=options):
        yield event


async def query_simple(
    prompt: str,
    cwd: Optional[Union[str, Path]] = None,
    permission_mode: str = "bypassPermissions",
) -> AsyncIterator[Any]:
    """Execute a simple query with default high-trust options.

    Convenience function for common use cases.

    Args:
        prompt: The prompt to send.
        cwd: Optional working directory.
        permission_mode: Permission mode (default: bypassPermissions).

    Yields:
        SDK events from the query response.
    """
    options = create_high_trust_options(
        cwd=cwd,
        permission_mode=permission_mode,
    )

    async for event in query_with_options(prompt, options):
        yield event
