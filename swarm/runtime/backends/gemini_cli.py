"""gemini_cli - Gemini CLI subprocess backend.

Owns process/thread lifecycle and run artifact wiring for the
``gemini-cli`` backend. Pure prompt/event helpers live in gemini_support.
"""

from __future__ import annotations

import logging
import os
import shutil
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
from .gemini_support import (
    build_prompt,
    build_stub_command,
    map_gemini_event,
)

logger = logging.getLogger(__name__)


class GeminiCliBackend(RunBackend):
    """Backend that uses Gemini CLI for run execution.

    This backend executes flows using the Gemini CLI tool, streaming JSONL
    events and mapping them to the standard RunEvent format.

    The Gemini CLI is expected to output JSONL events with types:
    - init: Backend initialization
    - message: Assistant text output
    - tool_use: Tool invocation started
    - tool_result: Tool invocation completed
    - error: Error occurred
    - result: Final completion result

    TODO: Implementation status (v0.7.1)
    ------------------------------------
    Currently this backend uses a stub command that echoes simulated JSONL events.
    The real implementation will use `gemini --output-format stream-json` as
    documented in the Gemini CLI docs.

    When implementing for real:
    1. Replace _build_command() stub with actual `gemini` CLI invocation
    2. The CLI should be called with `--output-format stream-json`
    3. Events map to RunEvent via _map_gemini_event()
    4. See docs/runtime/gemini-cli-backend.md for full integration plan
    """

    def __init__(self, repo_root: Optional[Path] = None):
        self._repo_root = repo_root or Path(__file__).resolve().parents[3]
        self._running_processes: Dict[RunId, subprocess.Popen[str]] = {}
        self._lock = threading.Lock()

        # CLI configuration
        self.gemini_cmd = os.environ.get("SWARM_GEMINI_CLI", "gemini")
        self.stub_mode = os.environ.get("SWARM_GEMINI_STUB", "1") == "1"
        self.cli_available = shutil.which(self.gemini_cmd) is not None

    @property
    def id(self) -> BackendId:
        return "gemini-cli"

    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            id="gemini-cli",
            label="Gemini CLI",
            supports_streaming=True,
            supports_events=True,
            supports_cancel=True,
            supports_replay=False,
        )

    def start(self, spec: RunSpec) -> RunId:
        """Start a run by invoking Gemini CLI commands."""
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
        """Execute the run in a background thread using Gemini CLI."""
        import json

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
                payload={"backend": "gemini-cli"},
            ),
        )

        # Log backend initialization event with mode indicator
        mode = "stub" if self.stub_mode or not self.cli_available else "real"
        storage.append_event(
            run_id,
            RunEvent(
                run_id=run_id,
                ts=datetime.now(timezone.utc),
                kind="backend_init",
                flow_key=spec.flow_keys[0] if spec.flow_keys else "unknown",
                payload={
                    "backend": "gemini-cli",
                    "version": "1.0.0",
                    "mode": mode,
                    "cli_available": self.cli_available,
                },
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

                # Build Gemini CLI command (pass run_id explicitly)
                cmd, env = self._build_command(flow_key, run_id, spec)

                # Prepare environment variables
                process_env = os.environ.copy()
                process_env.update(env)

                # Execute command and stream JSONL output
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

                # Process JSONL output line by line for streaming
                if process.stdout:
                    for line in process.stdout:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            gemini_event = json.loads(line)
                            mapped_event = self._map_gemini_event(run_id, flow_key, gemini_event)
                            if mapped_event:
                                storage.append_event(run_id, mapped_event)
                        except json.JSONDecodeError:
                            # Non-JSON output - log as text event
                            storage.append_event(
                                run_id,
                                RunEvent(
                                    run_id=run_id,
                                    ts=datetime.now(timezone.utc),
                                    kind="log",
                                    flow_key=flow_key,
                                    payload={"message": line},
                                ),
                            )

                # Wait for process to complete
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
                    error_msg = (
                        f"Flow {flow_key} failed: {stderr[:500]}"
                        if stderr
                        else f"Flow {flow_key} failed with code {process.returncode}"
                    )
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
            logger.exception("Error executing run %s in gemini-cli backend", run_id)
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

    # Pure helpers live in gemini_support; exposed as static methods to keep
    # the established `backend._build_prompt(...)` call surface.
    _build_prompt = staticmethod(build_prompt)
    _build_stub_command = staticmethod(build_stub_command)
    _map_gemini_event = staticmethod(map_gemini_event)

    def _build_command(
        self, flow_key: str, run_id: RunId, spec: RunSpec
    ) -> Tuple[List[str], Dict[str, str]]:
        """Build the Gemini CLI command to execute a flow.

        Uses real `gemini` CLI when available and SWARM_GEMINI_STUB=0.
        Falls back to stub for CI or when CLI is not installed.

        Args:
            flow_key: The flow being executed
            run_id: The run identifier (passed explicitly from _execute_run)
            spec: The run specification

        Returns:
            Tuple containing:
            - List of command arguments for safe subprocess execution.
            - Dictionary of environment variables.
        """
        env: Dict[str, str] = {}
        if run_id:
            env["RUN_ID"] = run_id

        # Use stub when stub_mode is enabled or CLI not available
        if self.stub_mode or not self.cli_available:
            logger.debug(
                "GeminiCliBackend using stub (stub_mode=%s, cli_available=%s)",
                self.stub_mode,
                self.cli_available,
            )
            return self._build_stub_command(flow_key), env

        # Build real gemini CLI command
        prompt = self._build_prompt(flow_key, run_id, spec)

        args = [
            self.gemini_cmd,
            "--output-format",
            "stream-json",
            "--prompt",
            prompt,
        ]

        return args, env

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
