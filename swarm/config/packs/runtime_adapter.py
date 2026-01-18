"""Runtime-facing adapter for resolved pack configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .models import EngineSettings, ResolvedRuntimeConfig
from .resolver import resolve_pack_config


def resolve_runtime(
    repo_root: Optional[Path] = None,
    cli_overrides: Optional[Dict[str, Any]] = None,
) -> ResolvedRuntimeConfig:
    """Resolve runtime configuration through pack hierarchy."""
    resolved = resolve_pack_config(repo_root=repo_root, cli_overrides=cli_overrides)

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

    features: Dict[str, Tuple[Any, str]] = {}
    for key in ["stepwise_execution", "context_handoff", "write_transcripts", "write_receipts"]:
        full_key = f"features.{key}"
        value = resolved.config.get(full_key)
        prov = resolved.provenance.get(full_key)
        if value is not None:
            features[key] = (value, prov.source if prov else "default")

    runtime: Dict[str, Tuple[Any, str]] = {}
    for key in [
        "context_budget_chars",
        "history_max_recent_chars",
        "history_max_older_chars",
        "timeout_seconds",
    ]:
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
    """Get engine mode using pack resolution."""
    resolved = resolve_runtime(repo_root=repo_root)
    settings = resolved.engines.get(engine_id)
    if settings:
        return settings.mode, settings.mode_source
    return "stub", "default"


def get_engine_execution_from_pack(
    engine_id: str,
    repo_root: Optional[Path] = None,
) -> Tuple[str, str]:
    """Get engine execution pattern using pack resolution."""
    resolved = resolve_runtime(repo_root=repo_root)
    settings = resolved.engines.get(engine_id)
    if settings:
        return settings.execution, settings.execution_source
    return "legacy", "default"
