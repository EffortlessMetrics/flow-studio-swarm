"""API adapter over the canonical runtime run state.

``swarm.runtime.types.RunState`` and ``run_state.json`` own the durable program
counter.  This service supplies the older HTTP field names as a compatibility
projection; it does not maintain a second state authority or cache stale state
across executor writes.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from swarm.runtime.run_factory import initialize_run
from swarm.runtime.safe_paths import validate_path_component
from swarm.runtime.types import RunSpec

logger = logging.getLogger(__name__)


class RunStateManager:
    """Read and mutate the canonical run state through an HTTP projection."""

    def __init__(self, runs_root: Path):
        self.runs_root = runs_root
        # Retained for source compatibility only. Reads always come from disk so
        # executor updates cannot be hidden by an API-process cache.
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._locks: Dict[str, asyncio.Lock] = {}

    def _get_lock(self, run_id: str) -> asyncio.Lock:
        if run_id not in self._locks:
            self._locks[run_id] = asyncio.Lock()
        return self._locks[run_id]

    def _compute_etag(self, state: Dict[str, Any]) -> str:
        content = json.dumps(state, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _state_path(self, run_id: str) -> Path:
        return self.runs_root / run_id / "run_state.json"

    @staticmethod
    def _synchronize_aliases(state: Dict[str, Any]) -> Dict[str, Any]:
        """Keep legacy HTTP names synchronized with runtime-owned fields."""
        flow_key = state.get("flow_key") or state.get("flow_id") or ""
        state["flow_key"] = flow_key
        state["flow_id"] = flow_key

        current_step = (
            state.get("current_step_id")
            or state.get("current_node")
            or state.get("current_step")
        )
        state["current_step_id"] = current_step
        state["current_node"] = current_step
        state["current_step"] = current_step

        completed = list(state.get("completed_nodes") or state.get("completed_steps") or [])
        state["completed_nodes"] = completed
        state["completed_steps"] = list(completed)

        state.setdefault("pending_steps", [])
        state.setdefault("context", {})
        state.setdefault("paused_at", None)
        state.setdefault("completed_at", None)
        state.setdefault("error", None)

        timestamp = state.get("timestamp") or datetime.now(timezone.utc).isoformat()
        state["timestamp"] = timestamp
        state.setdefault("created_at", timestamp)
        state.setdefault("updated_at", timestamp)
        return state

    def _load_state(self, run_id: str) -> Dict[str, Any]:
        state_path = self._state_path(run_id)
        if not state_path.exists():
            raise FileNotFoundError(f"Run '{run_id}' not found")
        state = json.loads(state_path.read_text(encoding="utf-8"))
        return self._synchronize_aliases(state)

    async def create_run(
        self,
        flow_id: str,
        run_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        start_step: Optional[str] = None,
        *,
        mode: str = "execute",
        backend: str = "claude-step-orchestrator",
        initiator: str = "api",
    ) -> Dict[str, Any]:
        """Create one complete constitutional run record."""
        validate_path_component(flow_id, "flow_id")
        if run_id:
            validate_path_component(run_id, "run_id")
        else:
            run_id = (
                f"{flow_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-"
                f"{uuid.uuid4().hex[:8]}"
            )

        spec = RunSpec(
            flow_keys=[flow_id],
            backend=backend,
            initiator=initiator,
            params={
                "mode": mode,
                "initial_context": dict(context or {}),
                "start_step": start_step,
            },
        )
        initialized = initialize_run(
            run_id,
            spec,
            flow_key=flow_id,
            start_step=start_step,
            mode=mode,
            runs_dir=self.runs_root,
        )

        state = json.loads(
            (initialized.path / "run_state.json").read_text(encoding="utf-8")
        )
        now = initialized.summary.created_at.isoformat()
        state.update(
            {
                "current_step": start_step,
                "completed_steps": [],
                "pending_steps": [],
                "context": dict(context or {}),
                "created_at": now,
                "updated_at": now,
                "paused_at": None,
                "completed_at": None,
                "error": None,
            }
        )
        await self._save_state(run_id, state)
        return self._synchronize_aliases(state)

    def _get_run_unlocked(self, run_id: str) -> tuple[Dict[str, Any], str]:
        state = self._load_state(run_id)
        return state, self._compute_etag(state)

    async def get_run(self, run_id: str) -> tuple[Dict[str, Any], str]:
        validate_path_component(run_id, "run_id")
        async with self._get_lock(run_id):
            return self._get_run_unlocked(run_id)

    async def update_run(
        self,
        run_id: str,
        updates: Dict[str, Any],
        expected_etag: Optional[str] = None,
    ) -> tuple[Dict[str, Any], str]:
        """Update canonical state while preserving runtime/API aliases."""
        validate_path_component(run_id, "run_id")
        async with self._get_lock(run_id):
            state, current_etag = self._get_run_unlocked(run_id)
            if expected_etag and expected_etag != current_etag:
                raise ValueError(f"ETag mismatch: expected {expected_etag}, got {current_etag}")

            state.update(updates)
            now = datetime.now(timezone.utc).isoformat()
            state["updated_at"] = now
            state["timestamp"] = now

            if "current_step" in updates:
                state["current_step_id"] = updates["current_step"]
                state["current_node"] = updates["current_step"]
            elif "current_step_id" in updates:
                state["current_step"] = updates["current_step_id"]
                state["current_node"] = updates["current_step_id"]

            if "completed_steps" in updates:
                state["completed_nodes"] = list(updates["completed_steps"])
            elif "completed_nodes" in updates:
                state["completed_steps"] = list(updates["completed_nodes"])

            if "flow_id" in updates:
                state["flow_key"] = updates["flow_id"]
            elif "flow_key" in updates:
                state["flow_id"] = updates["flow_key"]

            await self._save_state(run_id, state)
            projected = self._synchronize_aliases(state)
            return projected, self._compute_etag(projected)

    async def _save_state(self, run_id: str, state: Dict[str, Any]) -> None:
        state = self._synchronize_aliases(state)
        state_path = self._state_path(run_id)
        state_path.parent.mkdir(parents=True, exist_ok=True)

        tmp_path = state_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
        os.replace(tmp_path, state_path)
        self._cache[run_id] = dict(state)

    def list_runs(self, limit: int = 20) -> List[Dict[str, Any]]:
        """List recent canonical runs by state-file modification time."""
        if not self.runs_root.exists():
            return []

        candidates: List[tuple[float, Path]] = []
        with os.scandir(self.runs_root) as entries:
            for entry in entries:
                if entry.is_dir():
                    candidates.append((entry.stat().st_mtime, Path(entry.path)))
        candidates.sort(key=lambda item: item[0], reverse=True)

        runs: List[Dict[str, Any]] = []
        for _, run_dir in candidates:
            if len(runs) >= limit:
                break
            state_path = run_dir / "run_state.json"
            if not state_path.exists():
                continue
            try:
                state = self._synchronize_aliases(
                    json.loads(state_path.read_text(encoding="utf-8"))
                )
                runs.append(
                    {
                        "run_id": state.get("run_id", run_dir.name),
                        "flow_key": state.get("flow_key"),
                        "status": state.get("status"),
                        "timestamp": state.get("created_at") or state.get("timestamp"),
                    }
                )
            except (OSError, json.JSONDecodeError, TypeError) as exc:
                logger.warning("Failed to load run state %s: %s", run_dir, exc)
        return runs


_state_manager: Optional[RunStateManager] = None


def get_state_manager() -> RunStateManager:
    """Get or create the API adapter for the configured canonical run root."""
    global _state_manager
    if _state_manager is None:
        from swarm.api.server import get_spec_manager

        manager = get_spec_manager()
        _state_manager = RunStateManager(manager.runs_root)
    return _state_manager
