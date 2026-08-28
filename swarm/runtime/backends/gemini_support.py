"""gemini_support - Pure helpers for the Gemini CLI backend.

Prompt construction, stub-command construction, and Gemini -> RunEvent
mapping. These carry no backend instance state, so they live here to keep
gemini_cli.py focused on process lifecycle.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..types import (
    RunEvent,
    RunId,
    RunSpec,
)

logger = logging.getLogger(__name__)


# -------------------------------------------------------------------------
# TOML Commands vs Backend Prompts: Design Separation
# -------------------------------------------------------------------------
# There are two ways to invoke Gemini for Swarm flows:
#
# 1. INTERACTIVE CLI (Human Use):
#    Location: .gemini/commands/swarm/*.toml
#    Purpose: Human operators use these with `gemini /swarm/<flow>` to
#             interactively execute flows from the terminal.
#    Format: TOML files with description + prompt, supporting @{} file refs.
#    Example: `gemini /swarm/signal my-run-id`
#
# 2. PROGRAMMATIC BACKEND (Flow Studio Use):
#    Location: This file (_build_prompt, _build_command)
#    Purpose: Flow Studio's runtime calls Gemini via subprocess with
#             explicit --prompt arguments for machine-driven execution.
#    Format: Direct CLI invocation with --output-format stream-json.
#    Example: `gemini --output-format stream-json --prompt "..."`
#
# Why the separation?
# - TOML commands are optimized for human ergonomics (readable prompts,
#   file references, help text).
# - Backend prompts are optimized for programmatic control (structured
#   output, run_id injection, event streaming).
#
# Future: A command-driven backend variant could invoke the TOML commands
# directly (e.g., `gemini /swarm/signal {run_id}`), but this would require
# capturing and parsing their output differently than stream-json format.
# -------------------------------------------------------------------------


def build_prompt(flow_key: str, run_id: RunId, spec: RunSpec) -> str:
    """Build the prompt for the Gemini CLI.

    Includes flow context, run ID, and instructions for structured output.

    Args:
        flow_key: The flow being executed (signal, plan, build, etc.)
        run_id: The run identifier (passed explicitly, not from spec.params)
        spec: The run specification
    """
    title = spec.params.get("title", flow_key)

    return f"""You are the Gemini CLI backend executing a Swarm flow step.

Flow: {flow_key}
Run ID: {run_id}
Title: {title}

Instructions:
1. Read the flow spec from swarm/flows/flow-{flow_key}.md
2. Execute the flow step according to the spec
3. Write outputs to swarm/runs/{run_id}/{flow_key}/ following RUN_BASE conventions
4. Stream your progress as structured events

Be concise and focused on the task."""

def build_stub_command(flow_key: str) -> List[str]:
    """Build a stub command that simulates Gemini JSONL output for testing.

    Uses python to safely print lines without shell metacharacters.
    RUN_ID is retrieved from environment in the stub to verify propagation.

    Args:
        flow_key: The flow being executed
    """
    tool_input = f'{{"path": "swarm/flows/flow-{flow_key}.md"}}'
    stub_events = [
        f'{{"type": "init", "backend": "gemini-cli", "flow": "{flow_key}"}}',
        f'{{"type": "text", "message": "Starting flow {flow_key}"}}',
        f'{{"type": "tool_use", "tool": "read", "input": {tool_input}}}',
        '{{"type": "tool_result", "tool": "read", "success": true}}',
        f'{{"type": "result", "flow": "{flow_key}", "status": "complete"}}',
    ]

    # Create a python one-liner that prints each event on a new line
    # and then prints the legacy completion message
    events_str = "\\n".join(stub_events)

    # We construct a python script that prints these lines
    # This avoids shell metacharacter issues with 'echo -e'
    # AND we pass the content as argument to avoid python injection
    python_script = (
        "import os, sys; "
        "print(sys.argv[1]); "
        # Verify RUN_ID propagation by printing it from env
        'print(f\'Flow {os.environ.get("RUN_ID", "UNKNOWN")} completed\')'
    )

    return [sys.executable, "-c", python_script, events_str]

def map_gemini_event(
    run_id: RunId, flow_key: str, gemini_event: Dict[str, Any]
) -> Optional[RunEvent]:
    """Map Gemini JSONL events to RunEvent format.

    Gemini CLI stream-json event types:
    - init: Session initialization
    - message: Text output (has 'role' field: user/assistant)
    - tool_use: Tool invocation started
    - tool_result: Tool invocation completed
    - error: Error occurred
    - result: Final completion result
    """
    event_type = gemini_event.get("type", "unknown")
    now = datetime.now(timezone.utc)

    # Parse timestamp if present
    ts_str = gemini_event.get("timestamp")
    if ts_str:
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except ValueError:
            logger.warning("Failed to parse Gemini event timestamp: %r", ts_str)
            ts = now
    else:
        ts = now

    # Map Gemini event types to RunEvent kinds
    if event_type == "message":
        role = gemini_event.get("role", "assistant")
        kind = "assistant_message" if role == "assistant" else "user_message"
    elif event_type == "tool_use":
        kind = "tool_start"
    elif event_type == "tool_result":
        kind = "tool_end"
    elif event_type == "error":
        kind = "error"
    elif event_type == "result":
        kind = "step_complete"
    elif event_type == "init":
        kind = "backend_init"
    elif event_type == "text":  # Legacy stub format
        kind = "log"
    else:
        kind = event_type

    # Build payload based on event type
    payload: Dict[str, Any] = {}
    if event_type == "init":
        payload = {
            "backend": gemini_event.get("backend"),
            "flow": gemini_event.get("flow"),
        }
    elif event_type == "message":
        payload = {
            "role": gemini_event.get("role"),
            "content": gemini_event.get("content", ""),
        }
    elif event_type == "tool_use":
        payload = {
            "tool": gemini_event.get("tool") or gemini_event.get("name"),
            "input": gemini_event.get("input") or gemini_event.get("args"),
        }
    elif event_type == "tool_result":
        # Be conservative: default to False if success field is missing
        success = gemini_event.get("success")
        if success is None:
            logger.warning("Gemini tool_result missing 'success' field: %r", gemini_event)
            success = False
        payload = {
            "tool": gemini_event.get("tool") or gemini_event.get("name"),
            "success": success,
            "output": gemini_event.get("output") or gemini_event.get("result"),
        }
    elif event_type == "text":
        payload = {"message": gemini_event.get("message")}
    elif event_type == "error":
        payload = {
            "error": gemini_event.get("error") or gemini_event.get("message"),
        }
    elif event_type == "result":
        payload = {
            "flow": gemini_event.get("flow"),
            "status": gemini_event.get("status"),
        }
    else:
        # Pass through unknown events
        payload = gemini_event

    return RunEvent(
        run_id=run_id,
        ts=ts,
        kind=kind,
        flow_key=flow_key,
        payload=payload,
    )
