"""
routing.py - Re-exports from _routing_legacy.py for backwards compatibility.

This module re-exports all public symbols from _routing_legacy.py to maintain
the expected import path `from swarm.runtime.stepwise.routing import ...`.

The actual routing logic lives in _routing_legacy.py. This file exists purely
as a compatibility shim during the modularization refactor.

See _routing_legacy.py for full documentation.
"""

from ._routing_legacy import (
    # Elephant Protocol: Progress Tracking and Stall Detection
    ProgressDelta,
    ProgressEvidence,
    StallAnalysis,
    compute_error_signature,
    detect_stall,
    record_progress_evidence,
    create_stall_routing_signal,
    # Core routing functions
    create_routing_signal,
    route_step,
    build_routing_context,
    # Candidate-set pattern
    generate_routing_candidates,
)

__all__ = [
    # Elephant Protocol
    "ProgressDelta",
    "ProgressEvidence",
    "StallAnalysis",
    "compute_error_signature",
    "detect_stall",
    "record_progress_evidence",
    "create_stall_routing_signal",
    # Core routing
    "create_routing_signal",
    "route_step",
    "build_routing_context",
    # Candidate-set pattern
    "generate_routing_candidates",
]
