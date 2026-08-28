"""harness - Claude Code CLI / Make execution backends.

Contains ClaudeHarnessBackend (wraps existing CLI/Make execution) and
AgentSDKBackend (placeholder for the Claude Agent SDK path).
"""

from __future__ import annotations

import logging
import os
import shlex
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .. import storage
from ..types import (
    BackendCapabilities,
    BackendId,
    RunEvent,
    RunId,
    RunSpec,
    RunStatus,
    RunSummary,
    SDLCStatus,
    generate_run_id,
)
from .base import RunBackend

logger = logging.getLogger(__name__)


class ClaudeHarnessBackend(RunBackend):
    """Backend that wraps existing Claude Code CLI / Make execution.

    This backend:
    - Uses subprocess to run Make targets or slash commands
    - Writes run metadata to swarm/runs/<run_id>/
    - Tracks process state for running jobs
    """

    def __init__(self, repo_root: Optional[Path] = None):
        self._repo_root = repo_root or Path(__file__).resolve().parents[3]
        self._running_processes: Dict[RunId, subprocess.Popen[str]] = {}
        self._lock = threading.Lock()

    @property
    def id(self) -> BackendId:
        return "claude-harness"

    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            id="claude-harness",
            label="Claude Code CLI",
            supports_streaming=False,
            supports_events=True,
            supports_cancel=True,
            supports_replay=False,
        )

    def start(self, spec: RunSpec) -> RunId:
        """Start a run by invoking Make/CLI commands."""
        run_id = generate_run_id()
        now = datetime.now(timezone.utc)

        # Create run directory and write initial metadata
        storage.create_run_dir(run_id)
        storage.write_spec(run_id, spec)

        summary = RunSummary(
            id=run_id,
            spec=spec,
            status=RunStatus.PENDING,
            sdlc_status=SDLCStatus.UNKNOWN,
            created_at=now,
            updated_at=now,
        )
        storage.write_summary(run_id, summary)

        # Log initial event
        storage.append_event(
            run_id,
            RunEvent(
                run_id=run_id,
                ts=now,
                kind="run_created",
                flow_key=spec.flow_keys[0] if spec.flow_keys else "unknown",
                payload={
                    "flows": spec.flow_keys,
                    "backend": spec.backend,
                    "initiator": spec.initiator,
                },
            ),
        )

        # Start execution in background thread
        thread = threading.Thread(
            target=self._execute_run,
            args=(run_id, spec),
            daemon=True,
        )
        thread.start()

        return run_id

    def _execute_run(self, run_id: RunId, spec: RunSpec) -> None:
        """Execute the run in a background thread."""
        now = datetime.now(timezone.utc)

        # Update status to running
        storage.update_summary(
            run_id,
            {
                "status": RunStatus.RUNNING.value,
                "started_at": now.isoformat(),
                "updated_at": now.isoformat(),
            },
        )

        storage.append_event(
            run_id,
            RunEvent(
                run_id=run_id,
                ts=now,
                kind="run_started",
                flow_key=spec.flow_keys[0] if spec.flow_keys else "unknown",
            ),
        )

        error_msg = None
        final_status = RunStatus.SUCCEEDED
        sdlc_status = SDLCStatus.OK

        try:
            # Execute each flow in sequence
            for flow_key in spec.flow_keys:
                flow_start = datetime.now(timezone.utc)
                storage.append_event(
                    run_id,
                    RunEvent(
                        run_id=run_id,
                        ts=flow_start,
                        kind="flow_start",
                        flow_key=flow_key,
                    ),
                )

                # Build command based on flow
                cmd, env = self._build_command(flow_key, spec)

                # Prepare environment variables
                process_env = os.environ.copy()
                process_env.update(env)

                # Execute command
                process = subprocess.Popen(
                    cmd,
                    cwd=str(self._repo_root),
                    shell=False,
                    env=process_env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )

                with self._lock:
                    self._running_processes[run_id] = process

                _, stderr = process.communicate()

                with self._lock:
                    self._running_processes.pop(run_id, None)

                flow_end = datetime.now(timezone.utc)

                if process.returncode != 0:
                    storage.append_event(
                        run_id,
                        RunEvent(
                            run_id=run_id,
                            ts=flow_end,
                            kind="flow_error",
                            flow_key=flow_key,
                            payload={
                                "returncode": process.returncode,
                                "stderr": stderr[:1000] if stderr else None,
                            },
                        ),
                    )
                    final_status = RunStatus.FAILED
                    sdlc_status = SDLCStatus.ERROR
                    if stderr:
                        error_msg = f"Flow {flow_key} failed: {stderr[:500]}"
                    else:
                        error_msg = f"Flow {flow_key} failed with code {process.returncode}"
                    break
                else:
                    storage.append_event(
                        run_id,
                        RunEvent(
                            run_id=run_id,
                            ts=flow_end,
                            kind="flow_end",
                            flow_key=flow_key,
                            payload={
                                "duration_ms": int((flow_end - flow_start).total_seconds() * 1000),
                            },
                        ),
                    )

        except Exception as e:
            logger.exception("Error executing run %s in claude-harness backend", run_id)
            final_status = RunStatus.FAILED
            sdlc_status = SDLCStatus.ERROR
            error_msg = str(e)

        # Update final status
        completed_at = datetime.now(timezone.utc)
        storage.update_summary(
            run_id,
            {
                "status": final_status.value,
                "sdlc_status": sdlc_status.value,
                "completed_at": completed_at.isoformat(),
                "updated_at": completed_at.isoformat(),
                "error": error_msg,
            },
        )

        storage.append_event(
            run_id,
            RunEvent(
                run_id=run_id,
                ts=completed_at,
                kind="run_completed",
                flow_key=spec.flow_keys[-1] if spec.flow_keys else "unknown",
                payload={
                    "status": final_status.value,
                    "error": error_msg,
                },
            ),
        )

    def _build_command(self, flow_key: str, spec: RunSpec) -> Tuple[List[str], Dict[str, str]]:
        """Build the command arguments to execute a flow.

        Returns:
            Tuple containing:
            - List of arguments for safe subprocess execution
            - Dictionary of environment variables to set
        """
        env: Dict[str, str] = {}

        # Add run_id as environment variable if present
        run_id = spec.params.get("run_id", "")
        if run_id:
            env["RUN_ID"] = run_id

        # Map flow keys to Make targets or Claude commands
        flow_commands = {
            "signal": "make demo-signal",
            "plan": "make demo-plan",
            "build": "make demo-build",
            "gate": "make demo-gate",
            "deploy": "make demo-deploy",
            "wisdom": "make demo-wisdom",
        }

        # Use Make target if available
        if flow_key in flow_commands:
            cmd = flow_commands[flow_key]
            return shlex.split(cmd), env

        # Fallback to slash command style
        return ["echo", f"Flow {flow_key} would run here"], env

    def get_summary(self, run_id: RunId) -> Optional[RunSummary]:
        """Get summary from disk."""
        return storage.read_summary(run_id)

    def list_summaries(self) -> List[RunSummary]:
        """List all runs with summaries."""
        summaries: List[RunSummary] = []
        for rid in storage.list_runs():
            summary = storage.read_summary(rid)
            if summary:
                summaries.append(summary)
        return summaries

    def get_events(self, run_id: RunId) -> List[RunEvent]:
        """Get events from disk."""
        return storage.read_events(run_id)

    def cancel(self, run_id: RunId) -> bool:
        """Cancel a running process."""
        with self._lock:
            process = self._running_processes.get(run_id)
            if process:
                process.terminate()
                self._running_processes.pop(run_id, None)

                # Update status
                now = datetime.now(timezone.utc)
                storage.update_summary(
                    run_id,
                    {
                        "status": RunStatus.CANCELED.value,
                        "completed_at": now.isoformat(),
                        "updated_at": now.isoformat(),
                    },
                )
                storage.append_event(
                    run_id,
                    RunEvent(
                        run_id=run_id,
                        ts=now,
                        kind="run_canceled",
                        flow_key="unknown",
                    ),
                )
                return True
        return False

class AgentSDKBackend(RunBackend):
    """Backend that uses the Claude Agent SDK (stub for future implementation)."""

    @property
    def id(self) -> BackendId:
        return "claude-agent-sdk"

    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            id="claude-agent-sdk",
            label="Claude Agent SDK",
            supports_streaming=True,
            supports_events=True,
            supports_cancel=True,
            supports_replay=True,
        )

    def start(self, spec: RunSpec) -> RunId:
        raise NotImplementedError("Agent SDK backend not yet implemented")

    def get_summary(self, run_id: RunId) -> Optional[RunSummary]:
        return storage.read_summary(run_id)

    def list_summaries(self) -> List[RunSummary]:
        return []

    def get_events(self, run_id: RunId) -> List[RunEvent]:
        return storage.read_events(run_id)
