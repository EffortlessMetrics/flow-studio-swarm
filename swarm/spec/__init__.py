"""
swarm/spec - Spec-first architecture for stepwise execution.

This package provides the specification layer for the industrialized SDLC:
- StationSpec: Contract + runtime profile for execution roles
- FlowSpec: Orchestrator spine with routing configuration
- Fragments: Reusable prompt components
- Compiler: Assembles specs + context into SDK inputs

Usage:
    from swarm.spec import (
        StationSpec,
        FlowSpec,
        PromptPlan,
        load_station,
        load_flow,
        compile_prompt,
    )
"""

from .types import (
    StationSpec,
    StationSDK,
    StationIdentity,
    StationIO,
    StationHandoff,
    StationRuntimePrompt,
    FlowSpec,
    FlowStep,
    FlowDefaults,
    RoutingConfig,
    PromptPlan,
)

from .loader import (
    load_station,
    load_flow,
    load_fragment,
    list_stations,
    list_flows,
    validate_specs,
)

from .compiler import (
    compile_prompt,
    SpecCompiler,
)

__all__ = [
    # Types
    "StationSpec",
    "StationSDK",
    "StationIdentity",
    "StationIO",
    "StationHandoff",
    "StationRuntimePrompt",
    "FlowSpec",
    "FlowStep",
    "FlowDefaults",
    "RoutingConfig",
    "PromptPlan",
    # Loader
    "load_station",
    "load_flow",
    "load_fragment",
    "list_stations",
    "list_flows",
    "validate_specs",
    # Compiler
    "compile_prompt",
    "SpecCompiler",
]
