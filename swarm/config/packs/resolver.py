"""Pack configuration resolution with provenance tracking."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .hashing import compute_pack_hash
from .load import load_baseline_pack, load_repo_pack
from .lock import _pack_from_lock_config, read_pack_lock
from .models import EngineConfig, Pack, Provenance, ResolvedConfig
from .paths import get_baseline_pack_path, get_pack_lock_path, get_repo_pack_path

logger = logging.getLogger(__name__)


class PackResolver:
    """Resolves configuration through the pack layer hierarchy."""

    def __init__(
        self,
        repo_root: Optional[Path] = None,
        cli_overrides: Optional[Dict[str, Any]] = None,
        ignore_lock: bool = False,
    ):
        """Initialize the resolver."""
        self._repo_root = repo_root
        self._cli_overrides = cli_overrides or {}

        self._baseline = load_baseline_pack()
        self._repo_pack = load_repo_pack(repo_root) if repo_root else None

        self._pinned_pack: Optional[Pack] = None
        self._pin_path: Optional[str] = None
        self._pin_hash_valid: bool = True
        self._pin_hash_warning: Optional[str] = None

        if repo_root and not ignore_lock:
            self._load_pinned_pack(repo_root)

    def _load_pinned_pack(self, repo_root: Path) -> None:
        """Load pinned pack from lock file if it exists."""
        lock_path = get_pack_lock_path(repo_root)
        lock = read_pack_lock(lock_path)

        if lock is None:
            return

        self._pinned_pack = _pack_from_lock_config(lock)
        self._pin_path = str(lock_path)

        if self._repo_pack and lock.pack_hash:
            current_hash = compute_pack_hash(self._repo_pack)
            if lock.pack_hash != current_hash:
                self._pin_hash_valid = False
                self._pin_hash_warning = (
                    "Pack hash mismatch: lock file was generated from a different "
                    f"pack configuration. Lock hash: {lock.pack_hash[:12]}..., "
                    f"current: {current_hash[:12]}... "
                    "Consider regenerating the lock file with 'lock_current_pack()'."
                )
                logger.warning(self._pin_hash_warning)

    @property
    def pin_hash_valid(self) -> bool:
        """Check if the pinned pack hash matches current pack."""
        return self._pin_hash_valid

    @property
    def pin_hash_warning(self) -> Optional[str]:
        """Get the hash mismatch warning message if any."""
        return self._pin_hash_warning

    def resolve(self) -> ResolvedConfig:
        """Resolve all configuration with provenance."""
        config: Dict[str, Any] = {}
        provenance: Dict[str, Provenance] = {}

        for engine_id in ["claude", "gemini"]:
            engine_config, engine_prov = self._resolve_engine(engine_id)
            for key, value in engine_config.items():
                full_key = f"engines.{engine_id}.{key}"
                config[full_key] = value
                provenance[full_key] = engine_prov[key]

        feature_config, feature_prov = self._resolve_features()
        for key, value in feature_config.items():
            full_key = f"features.{key}"
            config[full_key] = value
            provenance[full_key] = feature_prov[key]

        runtime_config, runtime_prov = self._resolve_runtime()
        for key, value in runtime_config.items():
            full_key = f"runtime.{key}"
            config[full_key] = value
            provenance[full_key] = runtime_prov[key]

        return ResolvedConfig(config=config, provenance=provenance)

    def _resolve_engine(self, engine_id: str) -> Tuple[Dict[str, Any], Dict[str, Provenance]]:
        """Resolve engine configuration."""
        result: Dict[str, Any] = {}
        prov: Dict[str, Provenance] = {}

        for field in ["mode", "execution", "provider"]:
            value, source, path = self._resolve_value(
                cli_key=f"engines.{engine_id}.{field}",
                env_key=f"SWARM_{engine_id.upper()}_{field.upper()}",
                repo_getter=lambda p, f=field, e=engine_id: (
                    getattr(p.engines.get(e, EngineConfig()), f, None) if p else None
                ),
                baseline_getter=lambda p, f=field, e=engine_id: (
                    getattr(p.engines.get(e, EngineConfig()), f, None) if p else None
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
                repo_getter=lambda p, f=field: (getattr(p.features, f, None) if p else None),
                baseline_getter=lambda p, f=field: (getattr(p.features, f, None) if p else None),
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
                repo_getter=lambda p, f=field: (getattr(p.runtime, f, None) if p else None),
                baseline_getter=lambda p, f=field: (getattr(p.runtime, f, None) if p else None),
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
        pin_getter=None,
    ) -> Tuple[Optional[Any], str, Optional[str]]:
        """Resolve a single value through the layer hierarchy."""
        if pin_getter is None:
            pin_getter = baseline_getter

        if cli_key in self._cli_overrides:
            return (self._cli_overrides[cli_key], "cli", f"--{cli_key}")

        env_value = os.environ.get(env_key)
        if env_value is not None:
            if env_value.lower() in ("true", "1", "yes"):
                return (True, "env", env_key)
            if env_value.lower() in ("false", "0", "no"):
                return (False, "env", env_key)
            try:
                return (int(env_value), "env", env_key)
            except ValueError:
                return (env_value, "env", env_key)

        if self._repo_pack:
            repo_value = repo_getter(self._repo_pack)
            if repo_value is not None:
                path = ".swarm/pack.yaml"
                if self._repo_root:
                    path = str(get_repo_pack_path(self._repo_root))
                return (repo_value, "repo", path)

        if self._pinned_pack:
            pin_value = pin_getter(self._pinned_pack)
            if pin_value is not None:
                return (pin_value, "pin", self._pin_path)

        baseline_value = baseline_getter(self._baseline)
        if baseline_value is not None:
            return (baseline_value, "baseline", str(get_baseline_pack_path()))

        return (None, "default", None)


def resolve_pack_config(
    repo_root: Optional[Path] = None,
    cli_overrides: Optional[Dict[str, Any]] = None,
) -> ResolvedConfig:
    """Convenience function to resolve pack configuration."""
    resolver = PackResolver(repo_root=repo_root, cli_overrides=cli_overrides)
    return resolver.resolve()
