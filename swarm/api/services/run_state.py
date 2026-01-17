"""
Run state management service.

Extracted from routes/runs.py to separate state management logic from HTTP endpoints.
Provides in-memory cache with disk persistence for run state.
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

logger = logging.getLogger(__name__)


class RunStateManager:
    """Manages run state in memory and on disk.

    In-memory cache for fast access, with disk persistence for durability.
    """

    def __init__(self, runs_root: Path):
        self.runs_root = runs_root
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._locks: Dict[str, asyncio.Lock] = {}

    def _get_lock(self, run_id: str) -> asyncio.Lock:
        """Get or create a lock for a run."""
        if run_id not in self._locks:
            self._locks[run_id] = asyncio.Lock()
        return self._locks[run_id]

    def _compute_etag(self, state: Dict[str, Any]) -> str:
        """Compute ETag from state."""
        content = json.dumps(state, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _state_path(self, run_id: str) -> Path:
        """Get path to run state file."""
        return self.runs_root / run_id / "run_state.json"

    async def create_run(
        self,
        flow_id: str,
        run_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        start_step: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new run."""
        if run_id is None:
            run_id = f"{flow_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"

        now = datetime.now(timezone.utc).isoformat()

        state = {
            "run_id": run_id,
            "flow_id": flow_id,
            "status": "pending",
            "current_step": start_step,
            "completed_steps": [],
            "pending_steps": [],
            "context": context or {},
            "created_at": now,
            "updated_at": now,
            "paused_at": None,
            "completed_at": None,
            "error": None,
        }

        # Create run directory
        run_dir = self.runs_root / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        # Save state
        await self._save_state(run_id, state)

        return state

    def _get_run_unlocked(self, run_id: str) -> tuple[Dict[str, Any], str]:
        """Get run state without locking (internal use only)."""
        # Check cache first
        if run_id in self._cache:
            state = self._cache[run_id]
            return state, self._compute_etag(state)

        # Load from disk
        state_path = self._state_path(run_id)
        if not state_path.exists():
            raise FileNotFoundError(f"Run '{run_id}' not found")

        state = json.loads(state_path.read_text(encoding="utf-8"))
        self._cache[run_id] = state
        return state, self._compute_etag(state)

    async def get_run(self, run_id: str) -> tuple[Dict[str, Any], str]:
        """Get run state with ETag."""
        async with self._get_lock(run_id):
            return self._get_run_unlocked(run_id)

    async def update_run(
        self,
        run_id: str,
        updates: Dict[str, Any],
        expected_etag: Optional[str] = None,
    ) -> tuple[Dict[str, Any], str]:
        """Update run state with optional ETag check."""
        async with self._get_lock(run_id):
            state, current_etag = self._get_run_unlocked(run_id)

            if expected_etag and expected_etag != current_etag:
                raise ValueError(f"ETag mismatch: expected {expected_etag}, got {current_etag}")

            # Apply updates
            state.update(updates)
            state["updated_at"] = datetime.now(timezone.utc).isoformat()

            await self._save_state(run_id, state)
            return state, self._compute_etag(state)

    async def _save_state(self, run_id: str, state: Dict[str, Any]) -> None:
        """Save state to disk and cache."""
        state_path = self._state_path(run_id)
        state_path.parent.mkdir(parents=True, exist_ok=True)

        # Write atomically
        tmp_path = state_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
        os.replace(tmp_path, state_path)

        self._cache[run_id] = state

    def list_runs(self, limit: int = 20) -> List[Dict[str, Any]]:
        """List recent runs."""
        runs = []

        if not self.runs_root.exists():
            return runs

        # Get directories sorted by modification time
        run_dirs = []
        for item in self.runs_root.iterdir():
            if item.is_dir() and (item / "run_state.json").exists():
                run_dirs.append((item.stat().st_mtime, item))

        run_dirs.sort(key=lambda x: x[0], reverse=True)

        for _, run_dir in run_dirs[:limit]:
            state_path = run_dir / "run_state.json"
            try:
                state = json.loads(state_path.read_text(encoding="utf-8"))
                runs.append(
                    {
                        "run_id": state.get("run_id", run_dir.name),
                        "flow_key": state.get("flow_id", "").split("-")[-1]
                        if state.get("flow_id")
                        else None,
                        "status": state.get("status"),
                        "timestamp": state.get("created_at"),
                    }
                )
            except Exception as e:
                logger.warning("Failed to load run state %s: %s", run_dir, e)

        return runs


# Global state manager (initialized on first use)
_state_manager: Optional[RunStateManager] = None


def get_state_manager() -> RunStateManager:
    """Get or create the global state manager."""
    global _state_manager
    if _state_manager is None:
        from swarm.api.server import get_spec_manager

        manager = get_spec_manager()
        _state_manager = RunStateManager(manager.runs_root)
    return _state_manager
