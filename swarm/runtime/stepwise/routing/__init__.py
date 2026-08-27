"""
Routing subsystem for stepwise orchestration.

This package provides the unified routing logic for stepwise flow execution.
It implements the priority-based routing strategy defined in the routing
protocol:

1. Fast-path: Obvious deterministic cases (single edge, VERIFIED, terminal)
2. Deterministic: CEL/condition evaluation (if DETERMINISTIC_ONLY mode)
3. Navigator: Intelligent routing via Navigator agent (ASSIST/AUTHORITATIVE modes)
4. Envelope fallback: Legacy RoutingSignal from step finalization
5. Escalate: Human intervention required (no valid candidates)

The routing subsystem is designed to be:

- **Bounded**: Only considers edges defined in the flow graph
- **Auditable**: Produces structured explanation for every decision
- **Cheap**: Uses LLM (Navigator) only when truly needed
- **Mode-aware**: Respects RoutingMode (DETERMINISTIC_ONLY, ASSIST, AUTHORITATIVE)

Components:
    driver.py - Main route_step() function that orchestrates routing strategies
    _routing_legacy.py - Legacy routing functions (re-exported for compatibility)

Usage (canonical):
    from swarm.runtime.stepwise.routing import route_step, RoutingOutcome

    outcome = route_step(
        step=current_step,
        step_result=result,
        run_state=state,
        loop_state=loops,
        iteration=iter_count,
        routing_mode=RoutingMode.ASSIST,
    )

Usage (legacy - maintained for backwards compatibility):
    from swarm.runtime.stepwise.routing import (
        create_routing_signal,
        generate_routing_candidates,
        build_routing_context,
    )

See Also:
    - swarm/runtime/router.py: Core FlowGraph and edge routing logic
    - swarm/runtime/types.py: RoutingSignal, RoutingMode, and related types
    - docs/ROUTING_PROTOCOL.md: Full routing protocol documentation
"""

from __future__ import annotations

import warnings
from typing import Any

# =============================================================================
# Canonical routing API (from driver.py)
# =============================================================================
# The driver's route_step() is the single entry point for all routing decisions.
# Import it as the canonical route_step function.
from swarm.runtime.stepwise.routing.driver import (  # noqa: E402
    RoutingOutcome,
    route_step,  # Canonical routing function
)

# Backwards-compat alias for code that used route_step_unified.
#
# Deprecated since v3.0, scheduled for removal in v4.0. It is resolved lazily
# through the module __getattr__ below so that accessing it raises a
# DeprecationWarning; use route_step instead.
_DEPRECATED_ALIASES = {
    "route_step_unified": ("route_step", route_step),
}

# =============================================================================
# Legacy routing re-exports (backwards compatibility)
# =============================================================================
# These ensure existing imports like:
#   from .routing import create_routing_signal, build_routing_context
# continue to work unchanged.
from swarm.runtime.stepwise._routing_legacy import (  # noqa: E402
    # Elephant Protocol: Stall detection types
    ProgressDelta,
    ProgressEvidence,
    ReceiptReader,
    StallAnalysis,
    build_routing_context,
    compute_error_signature,
    # Routing signal creation
    create_routing_signal,
    create_stall_routing_signal,
    # Elephant Protocol: Stall detection functions
    detect_stall,
    # Candidate-set pattern
    generate_routing_candidates,
    record_progress_evidence,
)
from swarm.runtime.stepwise._routing_legacy import (  # noqa: E402
    route_step as route_step_legacy,  # Renamed to avoid collision
)

__all__ = [
    # ==========================================================================
    # Canonical routing API (driver.py)
    # ==========================================================================
    "route_step",  # Canonical routing function
    "RoutingOutcome",
    "route_step_unified",  # Deprecated alias for route_step; removal in v4.0
    # ==========================================================================
    # Legacy exports (backwards compatibility)
    # ==========================================================================
    "route_step_legacy",  # Legacy function (for explicit legacy usage)
    "create_routing_signal",
    "build_routing_context",
    "ReceiptReader",
    # Elephant Protocol: Stall detection types
    "ProgressDelta",
    "ProgressEvidence",
    "StallAnalysis",
    # Elephant Protocol: Stall detection functions
    "detect_stall",
    "record_progress_evidence",
    "create_stall_routing_signal",
    "compute_error_signature",
    # Candidate-set pattern
    "generate_routing_candidates",
]


def __getattr__(name: str) -> Any:
    """Resolve deprecated aliases, warning on use.

    Module-level ``__getattr__`` (PEP 562) is only consulted for names that are
    not already module globals, so the alias stays out of the namespace until
    something actually asks for it. That makes the access point observable and
    lets us warn exactly once per call site.
    """
    alias = _DEPRECATED_ALIASES.get(name)
    if alias is not None:
        canonical_name, target = alias
        warnings.warn(
            f"{__name__}.{name} is deprecated and will be removed in v4.0; "
            f"use {__name__}.{canonical_name} instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return target
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    """Include lazily-resolved deprecated aliases in dir().

    PEP 562 __getattr__ does not affect dir(), so without this the alias would
    look absent to reflection-based consumers even though it is a public
    __all__ export. Mirrors swarm/spec/compiler/__init__.py.
    """
    return sorted(list(globals().keys()) + list(_DEPRECATED_ALIASES.keys()))
