"""
swarm.runtime.stepwise - Modular stepwise orchestration package.

This package provides a modularized implementation of stepwise flow execution,
extracted from the monolithic orchestrator.py. The package is organized into
focused modules that can be tested and reasoned about independently.

Package Structure:
    types.py         - StepTxnInput/Output dataclasses, VerificationResult
    receipt_compat.py - Legacy receipt read/update (single source of truth)
    spec_facade.py   - FlowSpec/StationSpec caching + graph building
    verification.py  - Station verify block → checks + events
    routing.py       - Fallback routing: spec + config-based
    macro_routing.py - Flow-to-flow transitions (on_complete/on_failure)
    detours.py       - Interruption/resume stacks, depth limits
    run_lifecycle.py - Create/resume runs, state management
    step_executor.py - Hydrate + engine lifecycle + finalization
    loop.py          - Canonical async loop + StopController
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

from .types import (
    StepTxnInput,
    StepTxnOutput,
    VerificationResult,
    VerificationCheck,
)
from .receipt_compat import (
    read_receipt_field,
    update_receipt_routing,
)
from .spec_facade import (
    SpecFacade,
    load_flow_spec,
    load_station_spec,
)
from .routing import (
    create_routing_signal,
    route_step,
)
from .orchestrator import (
    FlowExecutionResult,
    StepwiseOrchestrator,
    get_orchestrator,
)

# Backwards compatibility alias
GeminiStepOrchestrator = StepwiseOrchestrator

__all__ = [
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
    # Orchestrator
    "FlowExecutionResult",  # Macro routing result with flow result + decision
    "StepwiseOrchestrator",
    "GeminiStepOrchestrator",  # Backwards compat alias
    "get_orchestrator",  # Factory function
]
