"""Pack registry for configuration resolution.

Packs are versioned bundles of swarm configuration that can be:
- Embedded in the runtime (baseline)
- Defined in the repo (.swarm/pack.yaml)
- Overridden via CLI or environment

The registry implements layered resolution with provenance tracking,
so the UI can show where each setting came from.

Resolution order (highest to lowest priority):
1. CLI flags (e.g., --mode=sdk)
2. Environment variables (e.g., SWARM_CLAUDE_EXECUTION=session)
3. Repo pack (.swarm/pack.yaml)
4. Pinned pack (.swarm/pack.lock.json)
5. Baseline pack (swarm/packs/baseline/)
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

logger = logging.getLogger(__name__)


# =============================================================================
# Pack Schema Types
# =============================================================================

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


# =============================================================================
# Pack Loading
# =============================================================================

def _parse_engine_config(data: Dict[str, Any]) -> EngineConfig:
    """Parse engine config from YAML data."""
    return EngineConfig(
        mode=data.get("mode"),
        execution=data.get("execution"),
        provider=data.get("provider"),
    )


def _parse_features_config(data: Dict[str, Any]) -> FeaturesConfig:
    """Parse features config from YAML data."""
    return FeaturesConfig(
        stepwise_execution=data.get("stepwise_execution"),
        context_handoff=data.get("context_handoff"),
        write_transcripts=data.get("write_transcripts"),
        write_receipts=data.get("write_receipts"),
    )


def _parse_runtime_config(data: Dict[str, Any]) -> RuntimeConfig:
    """Parse runtime config from YAML data."""
    return RuntimeConfig(
        context_budget_chars=data.get("context_budget_chars"),
        history_max_recent_chars=data.get("history_max_recent_chars"),
        history_max_older_chars=data.get("history_max_older_chars"),
        timeout_seconds=data.get("timeout_seconds"),
    )


def _parse_flow_config(data: Dict[str, Any]) -> FlowConfig:
    """Parse flow config from YAML data."""
    return FlowConfig(
        enabled=data.get("enabled", True),
        context_budgets=data.get("context_budgets"),
    )


def load_pack_from_file(path: Path) -> Optional[Pack]:
    """Load a pack from a YAML file.

    Args:
        path: Path to pack.yaml file.

    Returns:
        Parsed Pack, or None if file doesn't exist or is invalid.
    """
    if not path.exists():
        return None

    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data:
            # Empty pack is valid - uses defaults
            return Pack()

        engines = {}
        for engine_id, engine_data in data.get("engines", {}).items():
            if isinstance(engine_data, dict):
                engines[engine_id] = _parse_engine_config(engine_data)

        flows = {}
        for flow_id, flow_data in data.get("flows", {}).items():
            if isinstance(flow_data, dict):
                flows[flow_id] = _parse_flow_config(flow_data)

        return Pack(
            version=data.get("version", "1.0"),
            id=data.get("id"),
            description=data.get("description"),
            extends=data.get("extends"),
            engines=engines,
            features=_parse_features_config(data.get("features", {})),
            runtime=_parse_runtime_config(data.get("runtime", {})),
            flows=flows,
        )

    except (yaml.YAMLError, OSError) as e:
        logger.warning("Failed to load pack from %s: %s", path, e)
        return None


def get_baseline_pack_path() -> Path:
    """Get path to the baseline pack bundled with the runtime."""
    return Path(__file__).parent.parent / "packs" / "baseline" / "pack.yaml"


def load_baseline_pack() -> Pack:
    """Load the baseline pack that ships with the runtime.

    Returns:
        The baseline Pack. Returns empty Pack if baseline file is missing.
    """
    path = get_baseline_pack_path()
    pack = load_pack_from_file(path)
    if pack is None:
        logger.warning("Baseline pack not found at %s, using empty defaults", path)
        return Pack(id="baseline")
    return pack


def get_repo_pack_path(repo_root: Path) -> Path:
    """Get path to the repo pack."""
    return repo_root / ".swarm" / "pack.yaml"


def load_repo_pack(repo_root: Path) -> Optional[Pack]:
    """Load the repo pack from .swarm/pack.yaml.

    Args:
        repo_root: Repository root path.

    Returns:
        The repo Pack, or None if not present.
    """
    return load_pack_from_file(get_repo_pack_path(repo_root))


# =============================================================================
# Pack Resolution with Provenance
# =============================================================================

class PackResolver:
    """Resolves configuration through the pack layer hierarchy.

    Resolution order (highest to lowest priority):
    1. CLI flags
    2. Environment variables
    3. Repo pack (.swarm/pack.yaml)
    4. Pinned pack (.swarm/pack.lock.json) - not yet implemented
    5. Baseline pack

    Each resolved value includes provenance showing which layer it came from.
    """

    def __init__(
        self,
        repo_root: Optional[Path] = None,
        cli_overrides: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the resolver.

        Args:
            repo_root: Repository root for loading repo pack.
            cli_overrides: CLI flag overrides (e.g., {"engines.claude.mode": "sdk"}).
        """
        self._repo_root = repo_root
        self._cli_overrides = cli_overrides or {}

        # Load packs
        self._baseline = load_baseline_pack()
        self._repo_pack = load_repo_pack(repo_root) if repo_root else None

    def resolve(self) -> ResolvedConfig:
        """Resolve all configuration with provenance.

        Returns:
            ResolvedConfig with final values and provenance map.
        """
        config: Dict[str, Any] = {}
        provenance: Dict[str, Provenance] = {}

        # Resolve engine config
        for engine_id in ["claude", "gemini"]:
            engine_config, engine_prov = self._resolve_engine(engine_id)
            for key, value in engine_config.items():
                full_key = f"engines.{engine_id}.{key}"
                config[full_key] = value
                provenance[full_key] = engine_prov[key]

        # Resolve features
        feature_config, feature_prov = self._resolve_features()
        for key, value in feature_config.items():
            full_key = f"features.{key}"
            config[full_key] = value
            provenance[full_key] = feature_prov[key]

        # Resolve runtime
        runtime_config, runtime_prov = self._resolve_runtime()
        for key, value in runtime_config.items():
            full_key = f"runtime.{key}"
            config[full_key] = value
            provenance[full_key] = runtime_prov[key]

        return ResolvedConfig(config=config, provenance=provenance)

    def _resolve_engine(
        self, engine_id: str
    ) -> Tuple[Dict[str, Any], Dict[str, Provenance]]:
        """Resolve engine configuration."""
        result: Dict[str, Any] = {}
        prov: Dict[str, Provenance] = {}

        for field in ["mode", "execution", "provider"]:
            value, source, path = self._resolve_value(
                cli_key=f"engines.{engine_id}.{field}",
                env_key=f"SWARM_{engine_id.upper()}_{field.upper()}",
                repo_getter=lambda p, f=field, e=engine_id: (
                    getattr(p.engines.get(e, EngineConfig()), f, None)
                    if p else None
                ),
                baseline_getter=lambda p, f=field, e=engine_id: (
                    getattr(p.engines.get(e, EngineConfig()), f, None)
                    if p else None
                ),
            )
            if value is not None:
                result[field] = value
                prov[field] = Provenance(value=value, source=source, path=path)

        return result, prov

    def _resolve_features(self) -> Tuple[Dict[str, Any], Dict[str, Provenance]]:
        """Resolve feature flags."""
        result: Dict[str, Any] = {}
        prov: Dict[str, Provenance] = {}

        for field in [
            "stepwise_execution",
            "context_handoff",
            "write_transcripts",
            "write_receipts",
        ]:
            value, source, path = self._resolve_value(
                cli_key=f"features.{field}",
                env_key=f"SWARM_FEATURE_{field.upper()}",
                repo_getter=lambda p, f=field: (
                    getattr(p.features, f, None) if p else None
                ),
                baseline_getter=lambda p, f=field: (
                    getattr(p.features, f, None) if p else None
                ),
            )
            if value is not None:
                result[field] = value
                prov[field] = Provenance(value=value, source=source, path=path)

        return result, prov

    def _resolve_runtime(self) -> Tuple[Dict[str, Any], Dict[str, Provenance]]:
        """Resolve runtime settings."""
        result: Dict[str, Any] = {}
        prov: Dict[str, Provenance] = {}

        for field in [
            "context_budget_chars",
            "history_max_recent_chars",
            "history_max_older_chars",
            "timeout_seconds",
        ]:
            value, source, path = self._resolve_value(
                cli_key=f"runtime.{field}",
                env_key=f"SWARM_{field.upper()}",
                repo_getter=lambda p, f=field: (
                    getattr(p.runtime, f, None) if p else None
                ),
                baseline_getter=lambda p, f=field: (
                    getattr(p.runtime, f, None) if p else None
                ),
            )
            if value is not None:
                result[field] = value
                prov[field] = Provenance(value=value, source=source, path=path)

        return result, prov

    def _resolve_value(
        self,
        cli_key: str,
        env_key: str,
        repo_getter,
        baseline_getter,
    ) -> Tuple[Optional[Any], str, Optional[str]]:
        """Resolve a single value through the layer hierarchy.

        Returns:
            Tuple of (value, source, path).
        """
        # 1. CLI override
        if cli_key in self._cli_overrides:
            return (self._cli_overrides[cli_key], "cli", f"--{cli_key}")

        # 2. Environment variable
        env_value = os.environ.get(env_key)
        if env_value is not None:
            # Parse booleans and integers
            if env_value.lower() in ("true", "1", "yes"):
                return (True, "env", env_key)
            if env_value.lower() in ("false", "0", "no"):
                return (False, "env", env_key)
            try:
                return (int(env_value), "env", env_key)
            except ValueError:
                return (env_value, "env", env_key)

        # 3. Repo pack
        if self._repo_pack:
            repo_value = repo_getter(self._repo_pack)
            if repo_value is not None:
                path = ".swarm/pack.yaml"
                if self._repo_root:
                    path = str(get_repo_pack_path(self._repo_root))
                return (repo_value, "repo", path)

        # 4. Baseline pack
        baseline_value = baseline_getter(self._baseline)
        if baseline_value is not None:
            return (baseline_value, "baseline", str(get_baseline_pack_path()))

        return (None, "default", None)


def resolve_pack_config(
    repo_root: Optional[Path] = None,
    cli_overrides: Optional[Dict[str, Any]] = None,
) -> ResolvedConfig:
    """Convenience function to resolve pack configuration.

    Args:
        repo_root: Repository root for loading repo pack.
        cli_overrides: CLI flag overrides.

    Returns:
        ResolvedConfig with final values and provenance map.
    """
    resolver = PackResolver(repo_root=repo_root, cli_overrides=cli_overrides)
    return resolver.resolve()


# =============================================================================
# Bridge: Resolved Runtime Adapter
# =============================================================================
#
# This adapter bridges pack_registry (new) with runtime_config (legacy).
# It provides a single entry point that:
# 1. Resolves pack config (baseline + repo + env + cli)
# 2. Returns values compatible with get_engine_mode() etc.
# 3. Includes provenance for UI display
#


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
    """Complete resolved runtime configuration with provenance.

    This is the output of resolve_runtime() and provides all settings
    needed for engine initialization plus provenance for debugging/UI.
    """
    engines: Dict[str, EngineSettings]
    features: Dict[str, Tuple[Any, str]]  # (value, source)
    runtime: Dict[str, Tuple[Any, str]]   # (value, source)


def resolve_runtime(
    repo_root: Optional[Path] = None,
    cli_overrides: Optional[Dict[str, Any]] = None,
) -> ResolvedRuntimeConfig:
    """Resolve runtime configuration through pack hierarchy.

    This is the primary entry point for callers who need engine settings.
    It returns resolved values with provenance, suitable for:
    - Engine factory initialization
    - UI display of "where did this setting come from"
    - Debugging configuration issues

    Resolution order (highest to lowest priority):
    1. CLI flags (cli_overrides)
    2. Environment variables
    3. Repo pack (.swarm/pack.yaml)
    4. Baseline pack (swarm/packs/baseline/)
    5. Hardcoded defaults

    Args:
        repo_root: Repository root for loading repo pack.
        cli_overrides: CLI flag overrides.

    Returns:
        ResolvedRuntimeConfig with engine settings and provenance.
    """
    # Resolve pack config
    resolved = resolve_pack_config(repo_root=repo_root, cli_overrides=cli_overrides)

    # Build engine settings with provenance
    engines: Dict[str, EngineSettings] = {}

    for engine_id in ["claude", "gemini"]:
        mode_key = f"engines.{engine_id}.mode"
        exec_key = f"engines.{engine_id}.execution"
        prov_key = f"engines.{engine_id}.provider"

        mode_prov = resolved.provenance.get(mode_key)
        exec_prov = resolved.provenance.get(exec_key)
        provider_prov = resolved.provenance.get(prov_key)

        engines[engine_id] = EngineSettings(
            mode=resolved.config.get(mode_key, "stub"),
            execution=resolved.config.get(exec_key, "legacy"),
            provider=resolved.config.get(prov_key, ""),
            mode_source=mode_prov.source if mode_prov else "default",
            execution_source=exec_prov.source if exec_prov else "default",
            provider_source=provider_prov.source if provider_prov else "default",
        )

    # Build feature settings with provenance
    features: Dict[str, Tuple[Any, str]] = {}
    for key in ["stepwise_execution", "context_handoff", "write_transcripts", "write_receipts"]:
        full_key = f"features.{key}"
        value = resolved.config.get(full_key)
        prov = resolved.provenance.get(full_key)
        if value is not None:
            features[key] = (value, prov.source if prov else "default")

    # Build runtime settings with provenance
    runtime: Dict[str, Tuple[Any, str]] = {}
    for key in ["context_budget_chars", "history_max_recent_chars", "history_max_older_chars", "timeout_seconds"]:
        full_key = f"runtime.{key}"
        value = resolved.config.get(full_key)
        prov = resolved.provenance.get(full_key)
        if value is not None:
            runtime[key] = (value, prov.source if prov else "default")

    return ResolvedRuntimeConfig(
        engines=engines,
        features=features,
        runtime=runtime,
    )


def get_engine_mode_from_pack(
    engine_id: str,
    repo_root: Optional[Path] = None,
) -> Tuple[str, str]:
    """Get engine mode using pack resolution.

    This is the pack-aware replacement for runtime_config.get_engine_mode().

    Args:
        engine_id: Engine identifier ("claude" or "gemini").
        repo_root: Repository root for loading repo pack.

    Returns:
        Tuple of (mode, source) where source is "cli"|"env"|"repo"|"baseline"|"default".
    """
    resolved = resolve_runtime(repo_root=repo_root)
    settings = resolved.engines.get(engine_id)
    if settings:
        return settings.mode, settings.mode_source
    return "stub", "default"


def get_engine_execution_from_pack(
    engine_id: str,
    repo_root: Optional[Path] = None,
) -> Tuple[str, str]:
    """Get engine execution pattern using pack resolution.

    This is the pack-aware replacement for runtime_config.get_engine_execution().

    Args:
        engine_id: Engine identifier ("claude" or "gemini").
        repo_root: Repository root for loading repo pack.

    Returns:
        Tuple of (execution, source) where execution is "legacy"|"session".
    """
    resolved = resolve_runtime(repo_root=repo_root)
    settings = resolved.engines.get(engine_id)
    if settings:
        return settings.execution, settings.execution_source
    return "legacy", "default"
