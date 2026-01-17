"""Deterministic hashing helpers for packs."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict

from .models import EngineConfig, FeaturesConfig, FlowConfig, Pack, RuntimeConfig


def _pack_to_hashable_dict(pack: Pack) -> Dict[str, Any]:
    """Convert a Pack to a dictionary suitable for hashing."""

    def engine_to_dict(ec: EngineConfig) -> Dict[str, Any]:
        return {
            "mode": ec.mode,
            "execution": ec.execution,
            "provider": ec.provider,
        }

    def features_to_dict(fc: FeaturesConfig) -> Dict[str, Any]:
        return {
            "stepwise_execution": fc.stepwise_execution,
            "context_handoff": fc.context_handoff,
            "write_transcripts": fc.write_transcripts,
            "write_receipts": fc.write_receipts,
        }

    def runtime_to_dict(rc: RuntimeConfig) -> Dict[str, Any]:
        return {
            "context_budget_chars": rc.context_budget_chars,
            "history_max_recent_chars": rc.history_max_recent_chars,
            "history_max_older_chars": rc.history_max_older_chars,
            "timeout_seconds": rc.timeout_seconds,
        }

    def flow_to_dict(fc: FlowConfig) -> Dict[str, Any]:
        return {
            "enabled": fc.enabled,
            "context_budgets": fc.context_budgets,
        }

    return {
        "version": pack.version,
        "id": pack.id,
        "description": pack.description,
        "extends": pack.extends,
        "engines": {k: engine_to_dict(v) for k, v in sorted(pack.engines.items())},
        "features": features_to_dict(pack.features),
        "runtime": runtime_to_dict(pack.runtime),
        "flows": {k: flow_to_dict(v) for k, v in sorted(pack.flows.items())},
    }


def compute_pack_hash(pack: Pack) -> str:
    """Compute SHA256 hash of pack content for integrity verification."""
    hashable = _pack_to_hashable_dict(pack)
    content = json.dumps(hashable, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
