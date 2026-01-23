"""Pack file loading helpers."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from swarm.utils.yaml_utils import load_yaml

from .models import EngineConfig, FeaturesConfig, FlowConfig, Pack, RuntimeConfig
from .paths import get_baseline_pack_path, get_repo_pack_path

logger = logging.getLogger(__name__)


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
            data = load_yaml(f)

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


def load_repo_pack(repo_root: Path) -> Optional[Pack]:
    """Load the repo pack from .swarm/pack.yaml.

    Args:
        repo_root: Repository root path.

    Returns:
        The repo Pack, or None if not present.
    """
    return load_pack_from_file(get_repo_pack_path(repo_root))
