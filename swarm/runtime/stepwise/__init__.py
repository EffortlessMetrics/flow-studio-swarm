"""
swarm.runtime.stepwise - Modular stepwise orchestration package.

This package provides a modularized implementation of stepwise flow execution,
extracted from the monolithic orchestrator.py. The package is organized into
focused modules that can be tested and reasoned about independently.

Package Structure:
    models.py        - FlowStepwiseSummary, FlowExecutionResult, ResolvedNode, RoutingOutcome
    graph_bridge.py  - FlowDefinition -> FlowGraph conversion for Navigator
    node_resolver.py - Node resolution (regular + injected nodes)
    envelope.py      - Envelope invariant enforcement
    routing.py       - Fallback routing: spec + config-based (shim for _routing_legacy.py)
    types.py         - StepTxnInput/Output dataclasses, VerificationResult
    receipt_compat.py - Legacy receipt read/update (single source of truth)
    spec_facade.py   - FlowSpec/StationSpec caching + graph building
    orchestrator.py  - Thin StepwiseOrchestrator coordinator

Usage:
    from swarm.runtime.stepwise import StepwiseOrchestrator
    from swarm.runtime.backends import GeminiCliBackend

    backend = GeminiCliBackend()
    engine = GeminiStepEngine(backend)
    orchestrator = StepwiseOrchestrator(engine)
    run_id = orchestrator.run_stepwise_flow("build", spec)

Backwards Compatibility:
    GeminiStepOrchestrator is an alias for StepwiseOrchestrator for
    backwards compatibility with existing code.
"""

# Modular components (new)
from .envelope import ensure_step_envelope
from .graph_bridge import build_flow_graph_from_definition
from .models import (
    FlowExecutionResult,
    FlowStepwiseSummary,
    ResolvedNode,
    RoutingOutcome,
)
from .node_resolver import find_step_index, get_next_node_id, resolve_node
from .orchestrator import (
    StepwiseOrchestrator,
    get_orchestrator,
)
from .receipt_compat import (
    read_receipt_field,
    update_receipt_routing,
)
from .routing import (
    create_routing_signal,
    route_step,
    # Elephant Protocol: Stall detection
    ProgressDelta,
    ProgressEvidence,
    StallAnalysis,
    detect_stall,
    record_progress_evidence,
    create_stall_routing_signal,
    compute_error_signature,
    # Candidate-set pattern
    generate_routing_candidates,
)
from .spec_facade import (
    SpecFacade,
    load_flow_spec,
    load_station_spec,
)
from .types import (
    StepTxnInput,
    StepTxnOutput,
    VerificationCheck,
    VerificationResult,
)

# Backwards compatibility alias
GeminiStepOrchestrator = StepwiseOrchestrator

__all__ = [
    # Modular components (new)
    "build_flow_graph_from_definition",
    "ensure_step_envelope",
    "find_step_index",
    "FlowExecutionResult",
    "FlowStepwiseSummary",
    "get_next_node_id",
    "ResolvedNode",
    "resolve_node",
    "RoutingOutcome",
    # Core types
    "StepTxnInput",
    "StepTxnOutput",
    "VerificationResult",
    "VerificationCheck",
    # Receipt handling
    "read_receipt_field",
    "update_receipt_routing",
    # Spec facade
    "SpecFacade",
    "load_flow_spec",
    "load_station_spec",
    # Routing
    "create_routing_signal",
    "route_step",
    # Elephant Protocol: Stall detection
    "ProgressDelta",
    "ProgressEvidence",
    "StallAnalysis",
    "detect_stall",
    "record_progress_evidence",
    "create_stall_routing_signal",
    "compute_error_signature",
    # Candidate-set pattern
    "generate_routing_candidates",
    # Orchestrator
    "StepwiseOrchestrator",
    "GeminiStepOrchestrator",  # Backwards compat alias
    "get_orchestrator",  # Factory function
]
