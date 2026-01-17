"""Pack configuration data models and resolved settings."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple


@dataclass
class EngineConfig:
    """Engine configuration from pack."""

    mode: Optional[str] = None
    execution: Optional[str] = None
    provider: Optional[str] = None


@dataclass
class FeaturesConfig:
    """Feature flags from pack."""

    stepwise_execution: Optional[bool] = None
    context_handoff: Optional[bool] = None
    write_transcripts: Optional[bool] = None
    write_receipts: Optional[bool] = None


@dataclass
class RuntimeConfig:
    """Runtime settings from pack."""

    context_budget_chars: Optional[int] = None
    history_max_recent_chars: Optional[int] = None
    history_max_older_chars: Optional[int] = None
    timeout_seconds: Optional[int] = None


@dataclass
class FlowConfig:
    """Per-flow configuration from pack."""

    enabled: bool = True
    context_budgets: Optional[Dict[str, int]] = None


@dataclass
class Pack:
    """A complete pack definition."""

    version: str = "1.0"
    id: Optional[str] = None
    description: Optional[str] = None
    extends: Optional[str] = None
    engines: Dict[str, EngineConfig] = field(default_factory=dict)
    features: FeaturesConfig = field(default_factory=FeaturesConfig)
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    flows: Dict[str, FlowConfig] = field(default_factory=dict)


@dataclass
class Provenance:
    """Tracks where a configuration value came from."""

    value: Any
    source: str  # "cli" | "env" | "repo" | "pin" | "baseline"
    path: Optional[str] = None  # e.g., ".swarm/pack.yaml" or "SWARM_CLAUDE_MODE"


@dataclass
class ResolvedConfig:
    """Fully resolved configuration with provenance."""

    config: Dict[str, Any]
    provenance: Dict[str, Provenance]


@dataclass
class PackLock:
    """Lock file content for pinning pack configuration."""

    version: str = "1.0"
    pack_hash: str = ""
    timestamp: str = ""
    pack_id: Optional[str] = None
    pack_version: str = "1.0"
    resolved_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EngineSettings:
    """Resolved engine settings with provenance."""

    mode: str
    execution: str
    provider: str
    mode_source: str  # "cli" | "env" | "repo" | "baseline" | "default"
    execution_source: str
    provider_source: str


@dataclass
class ResolvedRuntimeConfig:
    """Complete resolved runtime configuration with provenance."""

    engines: Dict[str, EngineSettings]
    features: Dict[str, Tuple[Any, str]]  # (value, source)
    runtime: Dict[str, Tuple[Any, str]]  # (value, source)
