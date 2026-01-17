"""Pack lockfile generation and verification."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .hashing import _pack_to_hashable_dict, compute_pack_hash
from .load import load_baseline_pack, load_repo_pack
from .models import EngineConfig, FeaturesConfig, FlowConfig, Pack, PackLock, RuntimeConfig
from .paths import get_pack_lock_path

logger = logging.getLogger(__name__)


def generate_pack_lock(pack: Pack, resolved_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Generate lock file content from a pack."""
    pack_hash = compute_pack_hash(pack)
    timestamp = datetime.now(timezone.utc).isoformat()

    lock_data = {
        "version": "1.0",
        "pack_hash": pack_hash,
        "timestamp": timestamp,
        "pack_id": pack.id,
        "pack_version": pack.version,
        "resolved_config": resolved_config or _pack_to_hashable_dict(pack),
    }

    return lock_data


def read_pack_lock(path: Path) -> Optional[PackLock]:
    """Read an existing pack lock file."""
    if not path.exists():
        return None

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        return PackLock(
            version=data.get("version", "1.0"),
            pack_hash=data.get("pack_hash", ""),
            timestamp=data.get("timestamp", ""),
            pack_id=data.get("pack_id"),
            pack_version=data.get("pack_version", "1.0"),
            resolved_config=data.get("resolved_config", {}),
        )

    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to read pack lock from %s: %s", path, e)
        return None


def write_pack_lock(path: Path, lock_data: Dict[str, Any]) -> bool:
    """Write lock file atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        fd, tmp_path = tempfile.mkstemp(
            suffix=".json",
            prefix="pack.lock.",
            dir=path.parent,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(lock_data, f, indent=2, sort_keys=True)
                f.write("\n")

            tmp_path_obj = Path(tmp_path)
            if path.exists():
                path.unlink()
            tmp_path_obj.rename(path)

            logger.info("Wrote pack lock to %s", path)
            return True

        except Exception:
            try:
                Path(tmp_path).unlink()
            except OSError:
                pass
            raise

    except (OSError, IOError) as e:
        logger.error("Failed to write pack lock to %s: %s", path, e)
        return False


def _pack_from_lock_config(lock: PackLock) -> Pack:
    """Reconstruct a Pack from lock file resolved_config."""
    config = lock.resolved_config

    engines = {}
    for engine_id, engine_data in config.get("engines", {}).items():
        if isinstance(engine_data, dict):
            engines[engine_id] = EngineConfig(
                mode=engine_data.get("mode"),
                execution=engine_data.get("execution"),
                provider=engine_data.get("provider"),
            )

    features_data = config.get("features", {})
    features = FeaturesConfig(
        stepwise_execution=features_data.get("stepwise_execution"),
        context_handoff=features_data.get("context_handoff"),
        write_transcripts=features_data.get("write_transcripts"),
        write_receipts=features_data.get("write_receipts"),
    )

    runtime_data = config.get("runtime", {})
    runtime = RuntimeConfig(
        context_budget_chars=runtime_data.get("context_budget_chars"),
        history_max_recent_chars=runtime_data.get("history_max_recent_chars"),
        history_max_older_chars=runtime_data.get("history_max_older_chars"),
        timeout_seconds=runtime_data.get("timeout_seconds"),
    )

    flows = {}
    for flow_id, flow_data in config.get("flows", {}).items():
        if isinstance(flow_data, dict):
            flows[flow_id] = FlowConfig(
                enabled=flow_data.get("enabled", True),
                context_budgets=flow_data.get("context_budgets"),
            )

    return Pack(
        version=config.get("version", lock.pack_version),
        id=config.get("id", lock.pack_id),
        description=config.get("description"),
        extends=config.get("extends"),
        engines=engines,
        features=features,
        runtime=runtime,
        flows=flows,
    )


def verify_pack_lock(lock: PackLock, current_pack: Pack) -> Tuple[bool, Optional[str]]:
    """Verify that a lock file matches the current pack state."""
    if not lock.pack_hash:
        return False, "Lock file has no pack_hash"

    current_hash = compute_pack_hash(current_pack)
    if lock.pack_hash != current_hash:
        return False, (
            f"Pack hash mismatch: lock has {lock.pack_hash[:12]}..., "
            f"current is {current_hash[:12]}..."
        )

    return True, None


def lock_current_pack(
    repo_root: Path,
    cli_overrides: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, str]:
    """Lock the current resolved pack configuration."""
    try:
        baseline = load_baseline_pack()
        repo_pack = load_repo_pack(repo_root)

        pack_to_lock = repo_pack if repo_pack else baseline
        resolved = _pack_to_hashable_dict(pack_to_lock)
        lock_data = generate_pack_lock(pack_to_lock, resolved_config=resolved)

        lock_path = get_pack_lock_path(repo_root)
        success = write_pack_lock(lock_path, lock_data)

        if success:
            return True, f"Locked pack configuration to {lock_path}"
        return False, f"Failed to write lock file to {lock_path}"

    except Exception as e:
        return False, f"Failed to lock pack: {e}"
