"""SDK import shim - handles importing claude_agent_sdk or claude_code_sdk.

This is the ONLY module that should import claude_agent_sdk or claude_code_sdk.
It provides a unified interface for SDK availability detection and module access.

Usage:
    from swarm.runtime._claude_sdk.sdk_import import (
        SDK_AVAILABLE,
        get_sdk_module,
        check_sdk_available,
        get_sdk_module_name,
    )
"""

from __future__ import annotations

import logging
from importlib.metadata import PackageNotFoundError, version as dist_version
from typing import Any, Optional

# Module logger
logger = logging.getLogger(__name__)

# =============================================================================
# SDK Availability Detection
# =============================================================================

SDK_AVAILABLE: bool = False
_sdk_module: Optional[Any] = None
_sdk_import_error: Optional[str] = None
_sdk_distribution: Optional[str] = None
_sdk_version: Optional[str] = None

try:
    # Prefer official Anthropic Agent SDK
    import claude_agent_sdk
    _sdk_module = claude_agent_sdk
    _sdk_distribution = "claude-agent-sdk"
    SDK_AVAILABLE = True
    logger.debug("claude_agent_sdk imported successfully")
except ImportError:
    try:
        # Fallback to legacy package name
        import claude_code_sdk
        _sdk_module = claude_code_sdk
        _sdk_distribution = "claude-code-sdk"
        SDK_AVAILABLE = True
        logger.debug("claude_code_sdk imported successfully (legacy)")
    except ImportError as e:
        _sdk_import_error = str(e)
        logger.debug("Claude SDK not available: %s", e)

if SDK_AVAILABLE and _sdk_distribution:
    try:
        _sdk_version = dist_version(_sdk_distribution)
    except PackageNotFoundError:
        _sdk_version = None


def get_sdk_module() -> Any:
    """Get the Claude SDK module.

    Returns:
        The claude_agent_sdk or claude_code_sdk module.

    Raises:
        ImportError: If SDK is not available.
    """
    if not SDK_AVAILABLE:
        raise ImportError(
            f"Claude SDK is not available: {_sdk_import_error}. "
            "Install with: pip install claude-agent-sdk (or claude-code-sdk)"
        )
    return _sdk_module


def check_sdk_available() -> bool:
    """Check if the Claude Code SDK is available.

    Returns:
        True if SDK can be imported, False otherwise.
    """
    return SDK_AVAILABLE


def get_sdk_module_name() -> Optional[str]:
    """Get the name of the loaded SDK module for debugging/receipts.

    Returns:
        The module name (e.g., "claude_agent_sdk" or "claude_code_sdk"),
        or None if SDK is not available.

    Example:
        >>> from swarm.runtime._claude_sdk.sdk_import import get_sdk_module_name
        >>> sdk_name = get_sdk_module_name()
        >>> # Returns "claude_agent_sdk" or "claude_code_sdk" or None
    """
    if SDK_AVAILABLE and _sdk_module is not None:
        return _sdk_module.__name__
    return None


def get_sdk_distribution() -> Optional[str]:
    """Return the installed SDK distribution name, if available."""
    return _sdk_distribution if SDK_AVAILABLE else None


def get_sdk_version() -> Optional[str]:
    """Return the installed SDK version, if available."""
    return _sdk_version if SDK_AVAILABLE else None
