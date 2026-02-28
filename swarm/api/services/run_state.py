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

from swarm.runtime.safe_paths import validate_path_component

logger = logging.getLogger(__name__)


class RunStateManager:
    """Manages run state in memory and on disk.

    In-memory cache for fast access, with disk persistence for durability.
    """

    def __init__(self, runs_root: Path):
        self.runs_root = runs_root
        self._cache: Dict[str, tuple[float, Dict[str, Any]]] = {}
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
        validate_path_component(flow_id, "flow_id")
        if run_id:
            validate_path_component(run_id, "run_id")

        if run_id is None:
            # Note: generated run_id is safe by construction (alphanumeric + hyphens)
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
        # Load from disk
        state_path = self._state_path(run_id)
        if not state_path.exists():
            raise FileNotFoundError(f"Run '{run_id}' not found")

        mtime = state_path.stat().st_mtime

        # Check cache first
        if run_id in self._cache:
            cached_mtime, state = self._cache[run_id]
            if mtime == cached_mtime:
                return state, self._compute_etag(state)

        state = json.loads(state_path.read_text(encoding="utf-8"))
        self._cache[run_id] = (mtime, state)
        return state, self._compute_etag(state)

    async def get_run(self, run_id: str) -> tuple[Dict[str, Any], str]:
        """Get run state with ETag."""
        validate_path_component(run_id, "run_id")
        async with self._get_lock(run_id):
            return self._get_run_unlocked(run_id)

    async def update_run(
        self,
        run_id: str,
        updates: Dict[str, Any],
        expected_etag: Optional[str] = None,
    ) -> tuple[Dict[str, Any], str]:
        """Update run state with optional ETag check."""
        validate_path_component(run_id, "run_id")
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

        self._cache[run_id] = (state_path.stat().st_mtime, state)

    def list_runs(self, limit: int = 20) -> List[Dict[str, Any]]:
        """List recent runs.

        Uses os.scandir for efficient directory traversal.
        Optimized to sort by mtime BEFORE checking file existence,
        reducing I/O overhead (stat calls) for large run histories.
        """
        runs = []

        if not self.runs_root.exists():
            return runs

        # Get directories and their modification times
        candidates = []
        with os.scandir(self.runs_root) as it:
            for entry in it:
                if entry.is_dir():
                    # capture mtime, path, and name
                    # entry.stat() is cached from scandir
                    candidates.append((entry.stat().st_mtime, entry.path, entry.name))

        # Sort by mtime descending (newest first)
        candidates.sort(key=lambda x: x[0], reverse=True)

        # Check for valid runs (run_state.json exists) in sorted order
        for mtime, run_path, run_id in candidates:
            if len(runs) >= limit:
                break

            try:
                # ⚡ Bolt: Cache-first strategy avoids expensive JSON parsing
                # and disk I/O for runs already loaded in memory and unmodified
                state_path = Path(run_path) / "run_state.json"

                # Use cached state if available and directory mtime hasn't changed.
                # In RunStateManager, modifying the state changes the directory mtime
                # (or at least closely tracks it since we write to the directory).
                # To be completely safe without a separate stat on run_state.json,
                # we do a full stat on state_path if we get a cache miss or mtime mismatch,
                # but the common case will hit.
                state = None
                if run_id in self._cache:
                    cached_mtime, cached_state = self._cache[run_id]
                    # Check if the cached file mtime is newer or equal to dir mtime
                    # (in case dir mtime was updated by something else, we fallback)
                    # For safety, if we aren't sure, we will just stat the file.
                    try:
                        file_mtime = state_path.stat().st_mtime
                        if file_mtime == cached_mtime:
                            state = cached_state
                    except FileNotFoundError:
                        continue

                if state is None:
                    if not state_path.exists():
                        continue
                    file_mtime = state_path.stat().st_mtime
                    state = json.loads(state_path.read_text(encoding="utf-8"))
                    self._cache[run_id] = (file_mtime, state)

                runs.append(
                    {
                        "run_id": state.get("run_id", run_id),
                        "flow_key": state.get("flow_id", "").split("-")[-1]
                        if state.get("flow_id")
                        else None,
                        "status": state.get("status"),
                        "timestamp": state.get("created_at"),
                    }
                )
            except Exception as e:
                logger.warning("Failed to load run state %s: %s", run_path, e)

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
