"""
engines.py - Step engine abstraction for pluggable LLM backends.

This module defines the interface for step execution engines, enabling
the same orchestrator to work with different LLM backends (Gemini, Claude, etc.).

Design Philosophy:
    - The orchestrator owns "which step to run" and "in what order"
    - The engine owns "how to execute a step" with a specific LLM
    - Engines emit RunEvents and return structured results
    - All engines write to the same RUN_BASE layout

Usage:
    from swarm.runtime.engines import StepEngine, StepContext, StepResult, GeminiStepEngine

    engine = GeminiStepEngine(repo_root)
    ctx = StepContext(...)
    result, events = engine.run_step(ctx)
"""

from __future__ import annotations

import json
import logging
import shlex
import shutil
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from swarm.config.flow_registry import TeachingNotes
from swarm.config.runtime_config import (
    ContextBudgetResolver,
    get_cli_path,
    get_context_budget_chars,
    get_history_max_older_chars,
    get_history_max_recent_chars,
    get_resolved_context_budgets,
    is_stub_mode,
)
from swarm.runtime.history_priority import (
    HistoryPriority,
    classify_history_item,
    get_priority_label,
    prioritize_history,
)
from swarm.runtime.path_helpers import (
    ensure_llm_dir,
    ensure_receipts_dir,
)
from swarm.runtime.path_helpers import (
    receipt_path as make_receipt_path,
)
from swarm.runtime.path_helpers import (
    transcript_path as make_transcript_path,
)

from .types import RunEvent, RunSpec

# Module logger
logger = logging.getLogger(__name__)


@dataclass
class StepContext:
    """Context provided to an engine for executing a single step.

    Contains all the information an engine needs to execute a step,
    including flow/step metadata, run specification, and history from
    previous steps for context building.

    Attributes:
        repo_root: Repository root path.
        run_id: The run identifier.
        flow_key: The flow being executed (signal, plan, build, etc.).
        step_id: The step identifier within the flow.
        step_index: 1-based step index within the flow.
        total_steps: Total number of steps in the flow.
        spec: The run specification.
        flow_title: Human-readable flow title.
        step_role: Description of what this step does.
        step_agents: Tuple of agent keys assigned to this step.
        history: List of previous step results for context.
        extra: Additional context-specific data.
    """

    repo_root: Path
    run_id: str
    flow_key: str
    step_id: str
    step_index: int
    total_steps: int
    spec: RunSpec
    flow_title: str
    step_role: str
    step_agents: Tuple[str, ...] = ()
    history: List[Dict[str, Any]] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)
    teaching_notes: Optional[TeachingNotes] = None
    routing: Optional["RoutingContext"] = None

    @property
    def run_base(self) -> Path:
        """Get the RUN_BASE path for this step's artifacts."""
        return Path(self.repo_root) / "swarm" / "runs" / self.run_id / self.flow_key


@dataclass
class RoutingContext:
    """Routing metadata for inclusion in receipts.

    Captures microloop state and routing decisions for observability.

    Attributes:
        loop_iteration: Current iteration count for the microloop (0-indexed).
        max_iterations: Maximum iterations allowed for the microloop.
        decision: Routing decision made ("loop", "advance", "terminate", "pending").
        reason: Human-readable reason for the routing decision.
    """

    loop_iteration: int = 0
    max_iterations: Optional[int] = None
    decision: str = "advance"  # "loop" | "advance" | "terminate" | "pending"
    reason: str = ""


@dataclass
class HistoryTruncationInfo:
    """Metadata about history truncation during prompt building.

    Used to track and report when history is dropped due to budget constraints.
    This enables monitoring, debugging, and tuning of context budgets.

    Attributes:
        steps_included: Number of history steps included in the prompt.
        steps_total: Total number of history steps available.
        chars_used: Characters used for history.
        budget_chars: Total character budget allowed.
        truncated: Whether any steps were omitted.
        priority_aware: Whether priority-based selection was used.
        priority_distribution: Counts of included items by priority level.
    """

    steps_included: int
    steps_total: int
    chars_used: int
    budget_chars: int
    truncated: bool = False
    priority_aware: bool = True
    priority_distribution: Optional[Dict[str, int]] = None

    @property
    def truncation_note(self) -> str:
        """Generate a machine-readable truncation note.

        Returns:
            Empty string if no truncation, otherwise a formatted note.
        """
        if not self.truncated:
            return ""
        omitted = self.steps_total - self.steps_included
        note = (
            f"[CONTEXT_TRUNCATED] Included {self.steps_included} of "
            f"{self.steps_total} history steps ({omitted} omitted, "
            f"budget: {self.chars_used:,}/{self.budget_chars:,} chars)"
        )
        if self.priority_aware and self.priority_distribution:
            dist = self.priority_distribution
            note += f" [Priority: CRITICAL={dist.get('CRITICAL', 0)}, HIGH={dist.get('HIGH', 0)}, MEDIUM={dist.get('MEDIUM', 0)}, LOW={dist.get('LOW', 0)}]"
        return note

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization in receipts."""
        result = {
            "steps_included": self.steps_included,
            "steps_total": self.steps_total,
            "chars_used": self.chars_used,
            "budget_chars": self.budget_chars,
            "truncated": self.truncated,
            "priority_aware": self.priority_aware,
        }
        if self.priority_distribution:
            result["priority_distribution"] = self.priority_distribution
        return result


@dataclass
class StepResult:
    """Result of executing a single step.

    Attributes:
        step_id: The step identifier.
        status: Execution status ("succeeded", "failed", "skipped").
        output: Summary text describing what happened.
        error: Error message if failed.
        duration_ms: Execution duration in milliseconds.
        artifacts: Optional dict of artifact paths/metadata produced.
    """

    step_id: str
    status: str  # "succeeded" | "failed" | "skipped"
    output: str
    error: Optional[str] = None
    duration_ms: int = 0
    artifacts: Optional[Dict[str, Any]] = None


class StepEngine(ABC):
    """Abstract base class for step execution engines.

    Engines are responsible for:
    - Taking a StepContext with all necessary metadata
    - Executing the step using their underlying LLM/CLI
    - Returning a StepResult and stream of RunEvents

    Engines do NOT own:
    - Flow traversal (that's the orchestrator's job)
    - Run lifecycle management (that's the backend's job)
    - Event persistence (that's the caller's job)
    """

    @property
    @abstractmethod
    def engine_id(self) -> str:
        """Unique identifier for this engine (e.g., 'gemini-step', 'claude-step')."""
        ...

    @abstractmethod
    def run_step(self, ctx: StepContext) -> Tuple[StepResult, Iterable[RunEvent]]:
        """Execute a step and return result + events.

        Args:
            ctx: Step execution context including flow/step metadata and history.

        Returns:
            Tuple of (StepResult, iterable of RunEvents produced during execution).
            Events should be yielded in chronological order.
        """
        ...


class GeminiStepEngine(StepEngine):
    """Step engine using Gemini CLI.

    Executes steps by invoking the Gemini CLI with step-specific prompts.
    Maps Gemini JSONL output to RunEvents.

    Configuration via environment:
        SWARM_GEMINI_CLI: Path to gemini CLI (default: "gemini")
        SWARM_GEMINI_STUB: Set to "1" to use stub mode for testing

    Context budgets are read from runtime.yaml via runtime_config.py.
    See docs/CONTEXT_BUDGETS.md for the full philosophy.
    """

    @property
    def HISTORY_BUDGET_CHARS(self) -> int:
        """Total budget for all previous step history (global default).

        Note: For flow-aware budgets, use _get_resolved_budgets() instead.
        """
        return get_context_budget_chars()

    @property
    def RECENT_STEP_MAX_CHARS(self) -> int:
        """Max chars for the most recent step output (global default).

        Note: For flow-aware budgets, use _get_resolved_budgets() instead.
        """
        return get_history_max_recent_chars()

    @property
    def OLDER_STEP_MAX_CHARS(self) -> int:
        """Max chars for older step outputs (global default).

        Note: For flow-aware budgets, use _get_resolved_budgets() instead.
        """
        return get_history_max_older_chars()

    def __init__(self, repo_root: Path, profile_id: Optional[str] = None):
        """Initialize the Gemini step engine.

        Args:
            repo_root: Repository root path.
            profile_id: Optional profile ID for flow-aware budget resolution.
        """
        self.repo_root = repo_root
        self._profile_id = profile_id
        self.gemini_cmd = get_cli_path("gemini")
        self.stub_mode = is_stub_mode("gemini")
        self.cli_available = shutil.which(self.gemini_cmd) is not None

    def _get_resolved_budgets(
        self, flow_key: Optional[str] = None, step_id: Optional[str] = None
    ):
        """Get resolved budgets for the given flow/step context.

        Uses the ContextBudgetResolver to cascade through step, flow, profile,
        and global defaults to determine effective budget values.

        Args:
            flow_key: Optional flow key for flow-level resolution.
            step_id: Optional step ID for step-level resolution.

        Returns:
            ContextBudgetConfig with resolved values.
        """
        return get_resolved_context_budgets(
            flow_key=flow_key,
            step_id=step_id,
            profile_id=self._profile_id,
        )

    @property
    def engine_id(self) -> str:
        return "gemini-step"

    def run_step(self, ctx: StepContext) -> Tuple[StepResult, Iterable[RunEvent]]:
        """Execute a step via Gemini CLI.

        Args:
            ctx: Step execution context.

        Returns:
            Tuple of (StepResult, list of RunEvents).
        """
        events: List[RunEvent] = []
        start_time = datetime.now(timezone.utc)

        # Build prompt from context (returns tuple with truncation info)
        prompt, truncation_info = self._build_prompt(ctx)

        # Stub mode for testing
        if self.stub_mode or not self.cli_available:
            logger.debug(
                "GeminiStepEngine using stub for step %s (stub_mode=%s, cli_available=%s)",
                ctx.step_id,
                self.stub_mode,
                self.cli_available,
            )
            end_time = datetime.now(timezone.utc)
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            result = StepResult(
                step_id=ctx.step_id,
                status="succeeded",
                output=f"[STUB] Step {ctx.step_id} completed successfully",
                duration_ms=duration_ms,
            )
            return result, events

        # Real execution via Gemini CLI
        try:
            output, cli_events = self._execute_gemini(ctx, prompt, truncation_info)
            events.extend(cli_events)

            end_time = datetime.now(timezone.utc)
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            result = StepResult(
                step_id=ctx.step_id,
                status="succeeded",
                output=output,
                duration_ms=duration_ms,
            )

        except Exception as e:
            logger.warning("Step %s failed: %s", ctx.step_id, e)
            end_time = datetime.now(timezone.utc)
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            result = StepResult(
                step_id=ctx.step_id,
                status="failed",
                output="",
                error=str(e),
                duration_ms=duration_ms,
            )

        return result, events

    def _build_prompt(
        self, ctx: StepContext
    ) -> Tuple[str, Optional[HistoryTruncationInfo]]:
        """Build a context-aware prompt for a step.

        Uses context budgeting to prevent prompts from growing unboundedly.
        Budget values are read from runtime.yaml (see docs/CONTEXT_BUDGETS.md):
        - Total history budget: HISTORY_BUDGET_CHARS (default: 200k chars)
        - Most recent step: RECENT_STEP_MAX_CHARS (default: 60k chars)
        - Older steps: OLDER_STEP_MAX_CHARS (default: 10k chars)
        - Stops adding history when budget is exceeded, adds truncation note

        Args:
            ctx: Step execution context.

        Returns:
            Tuple of (formatted prompt string, truncation info or None if no history).
        """
        lines = [
            f"# Flow: {ctx.flow_title}",
            f"# Step: {ctx.step_id} (Step {ctx.step_index} of {ctx.total_steps})",
            f"# Run ID: {ctx.run_id}",
            "",
            "## Step Role",
            ctx.step_role,
            "",
        ]

        # Agent assignments
        if ctx.step_agents:
            lines.append("## Assigned Agents")
            for agent in ctx.step_agents:
                lines.append(f"- {agent}")
            lines.append("")

        # Teaching notes (scoped context for this step)
        if ctx.teaching_notes:
            tn = ctx.teaching_notes

            if tn.inputs:
                lines.append("## Expected Inputs")
                lines.append("Read the following files/artifacts for this step:")
                for input_path in tn.inputs:
                    lines.append(f"- {input_path}")
                lines.append("")

            if tn.outputs:
                lines.append("## Expected Outputs")
                lines.append("Produce the following files/artifacts:")
                for output_path in tn.outputs:
                    lines.append(f"- {output_path}")
                lines.append("")

            if tn.emphasizes:
                lines.append("## Key Behaviors")
                lines.append("Focus on these patterns and behaviors:")
                for emphasis in tn.emphasizes:
                    lines.append(f"- {emphasis}")
                lines.append("")

            if tn.constraints:
                lines.append("## Constraints")
                lines.append("Observe these limitations:")
                for constraint in tn.constraints:
                    lines.append(f"- {constraint}")
                lines.append("")

        # RUN_BASE instructions
        lines.extend(
            [
                "## Output Location",
                f"Write outputs to: {ctx.run_base}/",
                "Follow RUN_BASE conventions for all artifacts.",
                "",
            ]
        )

        # Previous step context with priority-aware budget management
        truncation_info: Optional[HistoryTruncationInfo] = None

        if ctx.history:
            lines.append("## Previous Steps Context")
            lines.append("The following steps have already been completed:")
            lines.append("")

            # Get resolved budgets for this step's context
            budgets = self._get_resolved_budgets(ctx.flow_key, ctx.step_id)
            history_budget = budgets.context_budget_chars
            recent_max = budgets.history_max_recent_chars
            older_max = budgets.history_max_older_chars

            # Sort history by priority (CRITICAL first, then HIGH, MEDIUM, LOW)
            # Within same priority, maintain chronological order
            prioritized = prioritize_history(ctx.history)
            total_steps = len(ctx.history)

            # Track which items we include and their priorities
            included_items: List[Tuple[int, Dict[str, Any]]] = []  # (original_idx, item)
            priority_counts: Dict[str, int] = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
            chars_used = 0

            # Most recent step index for determining output limits
            most_recent_idx = total_steps - 1 if total_steps > 0 else -1

            # Process by priority order, including highest-value items first
            for priority, orig_idx, prev in prioritized:
                is_most_recent = orig_idx == most_recent_idx
                step_lines: List[str] = []

                status_emoji = "[OK]" if prev.get("status") == "succeeded" else "[FAIL]"
                priority_label = get_priority_label(priority)
                step_lines.append(f"### Step: {prev.get('step_id')} {status_emoji}")

                if prev.get("output"):
                    output = str(prev.get("output"))
                    # CRITICAL items get full recent budget, others based on recency
                    if priority >= HistoryPriority.CRITICAL:
                        max_chars = recent_max
                    elif is_most_recent:
                        max_chars = recent_max
                    else:
                        max_chars = older_max
                    if len(output) > max_chars:
                        output = output[:max_chars] + "... (truncated)"
                    step_lines.append(f"Output: {output}")

                if prev.get("error"):
                    error = str(prev.get("error"))
                    max_error = 200
                    if len(error) > max_error:
                        error = error[:max_error] + "... (truncated)"
                    step_lines.append(f"Error: {error}")

                step_lines.append("")

                # Calculate chars for this step
                step_text = "\n".join(step_lines)
                step_chars = len(step_text)

                # Check if adding this step would exceed budget
                if chars_used + step_chars > history_budget:
                    # Budget exceeded - skip lower priority items
                    continue

                # Include this item
                included_items.append((orig_idx, prev, step_lines))
                priority_counts[priority_label] += 1
                chars_used += step_chars

            # Sort included items back to chronological order for output
            included_items.sort(key=lambda x: x[0])

            # Build history lines in chronological order
            history_lines: List[str] = []
            for _, _, step_lines in included_items:
                history_lines.extend(step_lines)

            steps_included = len(included_items)

            # Track truncation metadata with priority information
            truncated = steps_included < total_steps
            truncation_info = HistoryTruncationInfo(
                steps_included=steps_included,
                steps_total=total_steps,
                chars_used=chars_used,
                budget_chars=history_budget,
                truncated=truncated,
                priority_aware=True,
                priority_distribution=priority_counts,
            )

            # Add machine-readable truncation warning if we didn't include all steps
            if truncated:
                truncation_warning = truncation_info.truncation_note
                history_lines.insert(0, truncation_warning + "\n")

                # Log for observability
                logger.debug(
                    "History truncation: %s (flow=%s, step=%s)",
                    truncation_warning,
                    ctx.flow_key,
                    ctx.step_id,
                )

            lines.extend(history_lines)

        # Instructions
        lines.extend(
            [
                "## Instructions",
                "1. Execute the step role as described above",
                "2. Use the assigned agent's capabilities and perspective",
                "3. Read any required inputs from previous steps or RUN_BASE",
                "4. Write all outputs to the correct RUN_BASE location",
                "5. Be concise and focused on the specific step",
                "",
            ]
        )

        return "\n".join(lines), truncation_info

    def _execute_gemini(
        self,
        ctx: StepContext,
        prompt: str,
        truncation_info: Optional[HistoryTruncationInfo] = None,
    ) -> Tuple[str, List[RunEvent]]:
        """Execute Gemini CLI and capture output.

        Captures assistant content from Gemini JSONL output and writes:
        - Transcript JSONL to RUN_BASE/llm/<step_id>-gemini.jsonl
        - Receipt JSON to RUN_BASE/receipts/<step_id>-gemini.json

        Args:
            ctx: Step execution context.
            prompt: The prompt to send to Gemini.
            truncation_info: Optional history truncation metadata for context budgets.

        Returns:
            Tuple of (actual assistant output text, list of events).

        Raises:
            RuntimeError: If execution fails.
        """
        events: List[RunEvent] = []
        start_time = datetime.now(timezone.utc)

        args = [
            self.gemini_cmd,
            "--output-format",
            "stream-json",
            "--prompt",
            prompt,
        ]
        cmd = " ".join(shlex.quote(a) for a in args)

        process = subprocess.Popen(
            cmd,
            cwd=str(self.repo_root),
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Collect raw events for transcript and track assistant content
        raw_events: List[Dict[str, Any]] = []
        full_assistant_text: List[str] = []
        token_counts: Dict[str, int] = {"prompt": 0, "completion": 0, "total": 0}

        if process.stdout:
            for line in process.stdout:
                line = line.strip()
                if not line:
                    continue

                # Try to parse and map to event
                try:
                    event_data = json.loads(line)
                    # Store raw event for transcript
                    raw_events.append(event_data)

                    # Extract assistant content from message events
                    event_type = event_data.get("type", "")
                    if event_type == "message":
                        role = event_data.get("role", "")
                        if role == "assistant":
                            content = event_data.get("content", "")
                            if content:
                                full_assistant_text.append(content)

                    # Extract token counts if available (standard format)
                    if "usage" in event_data:
                        usage = event_data["usage"]
                        if "prompt_tokens" in usage:
                            token_counts["prompt"] = usage["prompt_tokens"]
                        if "completion_tokens" in usage:
                            token_counts["completion"] = usage["completion_tokens"]
                        if "total_tokens" in usage:
                            token_counts["total"] = usage["total_tokens"]
                    # Some Gemini responses use different keys
                    if "promptTokenCount" in event_data:
                        token_counts["prompt"] = event_data["promptTokenCount"]
                    if "candidatesTokenCount" in event_data:
                        token_counts["completion"] = event_data["candidatesTokenCount"]
                    if "totalTokenCount" in event_data:
                        token_counts["total"] = event_data["totalTokenCount"]

                    event = self._map_gemini_event(ctx, event_data)
                    if event:
                        events.append(event)
                except json.JSONDecodeError:
                    # Log as text event and include in raw events
                    raw_events.append({"type": "text", "message": line})
                    events.append(
                        RunEvent(
                            run_id=ctx.run_id,
                            ts=datetime.now(timezone.utc),
                            kind="log",
                            flow_key=ctx.flow_key,
                            step_id=ctx.step_id,
                            payload={"message": line},
                        )
                    )

        _, stderr = process.communicate()
        end_time = datetime.now(timezone.utc)
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        if process.returncode != 0:
            error_msg = stderr[:500] if stderr else f"Exit code {process.returncode}"
            raise RuntimeError(f"Gemini CLI failed: {error_msg}")

        # Write transcript JSONL to RUN_BASE/llm/<step_id>-gemini.jsonl
        self._write_transcript(ctx, raw_events)

        # Write receipt JSON to RUN_BASE/receipts/<step_id>-gemini.json
        status = "succeeded"
        self._write_receipt(
            ctx, start_time, end_time, duration_ms, status, token_counts, truncation_info
        )

        # Build the actual assistant output text
        combined_text = "".join(full_assistant_text)
        if len(combined_text) > 2000:
            output_text = combined_text[:2000] + "... (truncated)"
        elif combined_text:
            output_text = combined_text
        else:
            # Fallback if no assistant content was captured
            output_text = f"Step {ctx.step_id} completed. Output lines: {len(raw_events)}"

        return output_text, events

    def _write_transcript(
        self, ctx: StepContext, raw_events: List[Dict[str, Any]]
    ) -> Path:
        """Write transcript JSONL to RUN_BASE/llm/<step_id>-<agent_key>-gemini.jsonl.

        Args:
            ctx: Step execution context.
            raw_events: List of raw Gemini events to write.

        Returns:
            Path to the transcript file.
        """
        agent_key = ctx.step_agents[0] if ctx.step_agents else "unknown"
        ensure_llm_dir(ctx.run_base)

        t_path = make_transcript_path(ctx.run_base, ctx.step_id, agent_key, "gemini")
        with t_path.open("w", encoding="utf-8") as f:
            for event in raw_events:
                # Add timestamp if not present
                if "timestamp" not in event:
                    event["timestamp"] = datetime.now(timezone.utc).isoformat() + "Z"
                f.write(json.dumps(event) + "\n")

        logger.debug("Wrote transcript to %s", t_path)
        return t_path

    def _write_receipt(
        self,
        ctx: StepContext,
        start_time: datetime,
        end_time: datetime,
        duration_ms: int,
        status: str,
        token_counts: Dict[str, int],
        truncation_info: Optional[HistoryTruncationInfo] = None,
    ) -> Path:
        """Write receipt JSON to RUN_BASE/receipts/<step_id>-<agent_key>.json.

        Args:
            ctx: Step execution context.
            start_time: When execution started.
            end_time: When execution completed.
            duration_ms: Execution duration in milliseconds.
            status: Execution status.
            token_counts: Token usage counts.
            truncation_info: Optional history truncation metadata for context budgets.

        Returns:
            Path to the receipt file.
        """
        agent_key = ctx.step_agents[0] if ctx.step_agents else "unknown"
        ensure_receipts_dir(ctx.run_base)

        r_path = make_receipt_path(ctx.run_base, ctx.step_id, agent_key)
        t_path = make_transcript_path(ctx.run_base, ctx.step_id, agent_key, "gemini")

        # Determine mode for receipt
        mode = "stub" if (self.stub_mode or not self.cli_available) else "cli"

        receipt = {
            "engine": self.engine_id,
            "mode": mode,
            "provider": "gemini",
            "model": "gemini",
            "step_id": ctx.step_id,
            "flow_key": ctx.flow_key,
            "run_id": ctx.run_id,
            "agent_key": agent_key,
            "started_at": start_time.isoformat() + "Z",
            "completed_at": end_time.isoformat() + "Z",
            "duration_ms": duration_ms,
            "status": status,
            "tokens": token_counts,
            "transcript_path": str(t_path.relative_to(ctx.run_base)),
        }

        # Add context truncation info if provided
        if truncation_info:
            receipt["context_truncation"] = truncation_info.to_dict()

        with r_path.open("w", encoding="utf-8") as f:
            json.dump(receipt, f, indent=2)

        logger.debug("Wrote receipt to %s", r_path)
        return r_path

    def _map_gemini_event(
        self,
        ctx: StepContext,
        gemini_event: Dict[str, Any],
    ) -> Optional[RunEvent]:
        """Map Gemini JSONL event to RunEvent.

        Args:
            ctx: Step execution context.
            gemini_event: Raw event from Gemini CLI.

        Returns:
            Mapped RunEvent or None if event should be skipped.
        """
        event_type = gemini_event.get("type", "unknown")
        now = datetime.now(timezone.utc)

        # Map event types
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
        elif event_type == "text":
            kind = "log"
        else:
            kind = event_type

        # Build payload
        payload: Dict[str, Any] = {}
        if event_type == "message":
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
            payload = {
                "tool": gemini_event.get("tool") or gemini_event.get("name"),
                "success": gemini_event.get("success", False),
                "output": gemini_event.get("output") or gemini_event.get("result"),
            }
        elif event_type == "text":
            payload = {"message": gemini_event.get("message")}
        elif event_type == "error":
            payload = {"error": gemini_event.get("error") or gemini_event.get("message")}
        else:
            payload = gemini_event

        return RunEvent(
            run_id=ctx.run_id,
            ts=now,
            kind=kind,
            flow_key=ctx.flow_key,
            step_id=ctx.step_id,
            agent_key=ctx.step_agents[0] if ctx.step_agents else None,
            payload=payload,
        )


class ClaudeStepEngine(StepEngine):
    """Step engine using Claude Agent SDK or CLI.

    This engine supports three modes:
    - stub: Returns synthetic results without calling real API (default, for CI/testing)
    - sdk: Uses the Claude Agent SDK to execute steps with real LLM calls
    - cli: Uses the Claude CLI (`claude --output-format stream-json`) for execution

    Mode is controlled by:
    1. SWARM_CLAUDE_STEP_ENGINE_MODE env var (stub, sdk, or cli)
    2. Config file swarm/config/runtime.yaml
    3. Default: stub

    Provider configuration (for sdk/cli modes):
    - anthropic: Direct Anthropic API (requires ANTHROPIC_API_KEY)
    - anthropic_compat: Anthropic-compatible endpoint like GLM/Z.AI
      (requires ANTHROPIC_API_KEY and optionally ANTHROPIC_BASE_URL)

    This engine writes transcript and receipt files to RUN_BASE so that the
    Flow Studio transcript/receipt API endpoints can display them.

    Transcript format: JSONL at RUN_BASE/llm/<step_id>-<agent>-claude.jsonl
    Receipt format: JSON at RUN_BASE/receipts/<step_id>-<agent>.json

    Tool mappings by step type:
    - Analysis steps: Read, Grep, Glob (read-only)
    - Build steps: Read, Write, Edit, Bash, Grep, Glob (full access)
    - Default: Read, Write, Edit, Bash, Grep, Glob

    Context budgets are read from runtime.yaml via runtime_config.py.
    See docs/CONTEXT_BUDGETS.md for the full philosophy.
    """

    @property
    def HISTORY_BUDGET_CHARS(self) -> int:
        """Total budget for all previous step history (global default).

        Note: For flow-aware budgets, use _get_resolved_budgets() instead.
        """
        return get_context_budget_chars()

    @property
    def RECENT_STEP_MAX_CHARS(self) -> int:
        """Max chars for the most recent step output (global default).

        Note: For flow-aware budgets, use _get_resolved_budgets() instead.
        """
        return get_history_max_recent_chars()

    @property
    def OLDER_STEP_MAX_CHARS(self) -> int:
        """Max chars for older step outputs (global default).

        Note: For flow-aware budgets, use _get_resolved_budgets() instead.
        """
        return get_history_max_older_chars()

    # Tool mappings by step type
    ANALYSIS_TOOLS = ["Read", "Grep", "Glob"]
    BUILD_TOOLS = ["Read", "Write", "Edit", "Bash", "Grep", "Glob"]
    DEFAULT_TOOLS = ["Read", "Write", "Edit", "Bash", "Grep", "Glob"]

    # Step ID patterns for tool selection
    ANALYSIS_STEP_PATTERNS = ["context", "analyze", "assess", "review", "audit", "check"]
    BUILD_STEP_PATTERNS = ["implement", "author", "write", "fix", "create", "mutate"]

    # JIT Finalization prompt template
    JIT_FINALIZATION_PROMPT = """
---
Your work session is complete. Now create a structured handoff for the next step.

Use the `Write` tool to create a file at: {handoff_path}

The file MUST be valid JSON with this exact structure:
```json
{{
  "step_id": "{step_id}",
  "flow_key": "{flow_key}",
  "run_id": "{run_id}",
  "status": "VERIFIED | UNVERIFIED | PARTIAL | BLOCKED",
  "summary": "2-paragraph summary of what you accomplished and any issues encountered",
  "artifacts": {{
    "artifact_name": "relative/path/from/run_base"
  }},
  "proposed_next_step": "step_id or null if flow should terminate",
  "notes_for_next_step": "What the next agent should know",
  "confidence": 0.0 to 1.0
}}
```

Guidelines:
- status: VERIFIED if you completed the task successfully, UNVERIFIED if tests fail or work is incomplete, PARTIAL if some work done but blocked, BLOCKED if you cannot proceed
- summary: Be concise but include what changed, what was tested, any concerns
- artifacts: List ALL files you created or modified (paths relative to run base)
- proposed_next_step: Based on your status and the flow spec, where should we go next?
- confidence: How confident are you in this handoff? (1.0 = very confident)

Write the file now.
---
"""

    # Router prompt template for agentic routing decisions
    ROUTER_PROMPT_TEMPLATE = """
You are a routing resolver. Your job is to analyze a step's handoff and decide the next move in the flow.

## Handoff from Previous Step

```json
{handoff_json}
```

## Step Routing Configuration

```yaml
step_id: {step_id}
flow_key: {flow_key}
routing:
  kind: {routing_kind}
  next: {routing_next}
  loop_target: {loop_target}
  loop_condition_field: {loop_condition_field}
  loop_success_values: {loop_success_values}
  max_iterations: {max_iterations}
current_iteration: {current_iteration}
```

## Decision Logic

Based on the handoff status and routing configuration:

1. If status is VERIFIED and routing kind is "linear" → decision: "advance" to next step
2. If status is VERIFIED and routing kind is "microloop" → decision: "advance" (exit loop)
3. If status is UNVERIFIED and routing kind is "microloop" and iterations < max → decision: "loop" back to loop_target
4. If status is UNVERIFIED and iterations >= max → decision: "advance" (exit loop with documented concerns)
5. If status is BLOCKED → decision: "terminate" (cannot proceed)
6. If status is PARTIAL → decision: "advance" but flag needs_human: true

## Output Format

Output ONLY a valid JSON object with this structure:
```json
{{
  "decision": "advance" | "loop" | "terminate" | "branch",
  "next_step_id": "<step_id or null>",
  "route": null,
  "reason": "<explanation for this routing decision>",
  "confidence": <0.0 to 1.0>,
  "needs_human": <true | false>
}}
```

Analyze the handoff and emit your routing decision now.
"""

    def __init__(
        self,
        repo_root: Optional[Path] = None,
        mode: Optional[str] = None,
        profile_id: Optional[str] = None,
        enable_stats_db: bool = True,
    ):
        """Initialize the Claude step engine.

        Args:
            repo_root: Repository root path.
            mode: Override mode selection ("stub", "sdk", or "cli").
                  If None, reads from config/environment.
            profile_id: Optional profile ID for flow-aware budget resolution.
            enable_stats_db: Whether to record stats to DuckDB. Default True.
        """
        from swarm.config.runtime_config import (
            get_cli_path,
            get_engine_mode,
            get_engine_provider,
        )

        self.repo_root = repo_root
        self._profile_id = profile_id

        # Determine mode: override > config > default
        if mode:
            self._mode = mode
        else:
            self._mode = get_engine_mode("claude")

        self.stub_mode = self._mode == "stub"
        self._sdk_available: Optional[bool] = None
        self._cli_available: Optional[bool] = None

        # Provider configuration
        self._provider = get_engine_provider("claude")
        self._cli_cmd = get_cli_path("claude")

        # Stats database for telemetry
        self._stats_db = None
        if enable_stats_db:
            try:
                from swarm.runtime.db import get_stats_db
                self._stats_db = get_stats_db()
            except Exception as e:
                logger.debug("StatsDB not available: %s", e)

        logger.debug(
            "ClaudeStepEngine initialized: mode=%s, provider=%s, cli_cmd=%s, stats_db=%s",
            self._mode,
            self._provider,
            self._cli_cmd,
            self._stats_db is not None,
        )

    @property
    def engine_id(self) -> str:
        return "claude-step"

    def _get_resolved_budgets(
        self, flow_key: Optional[str] = None, step_id: Optional[str] = None
    ):
        """Get resolved budgets for the given flow/step context.

        Uses the ContextBudgetResolver to cascade through step, flow, profile,
        and global defaults to determine effective budget values.

        Args:
            flow_key: Optional flow key for flow-level resolution.
            step_id: Optional step ID for step-level resolution.

        Returns:
            ContextBudgetConfig with resolved values.
        """
        return get_resolved_context_budgets(
            flow_key=flow_key,
            step_id=step_id,
            profile_id=self._profile_id,
        )

    def _check_sdk_available(self) -> bool:
        """Check if the Claude Agent SDK is available.

        Returns:
            True if the SDK can be imported, False otherwise.
        """
        if self._sdk_available is not None:
            return self._sdk_available

        try:
            import claude_code_sdk  # noqa: F401

            self._sdk_available = True
        except ImportError:
            self._sdk_available = False
            logger.debug("Claude Agent SDK not available, will use stub mode")

        return self._sdk_available

    def _check_cli_available(self) -> bool:
        """Check if the Claude CLI is available.

        Returns:
            True if the CLI executable can be found, False otherwise.
        """
        if self._cli_available is not None:
            return self._cli_available

        self._cli_available = shutil.which(self._cli_cmd) is not None
        if not self._cli_available:
            logger.debug(
                "Claude CLI not available at '%s', will use stub mode", self._cli_cmd
            )

        return self._cli_available

    def _get_tools_for_step(self, ctx: StepContext) -> List[str]:
        """Determine which tools to allow for a step based on its type.

        Args:
            ctx: Step execution context.

        Returns:
            List of tool names to allow.
        """
        step_id_lower = ctx.step_id.lower()
        step_role_lower = ctx.step_role.lower()

        # Check for analysis patterns
        for pattern in self.ANALYSIS_STEP_PATTERNS:
            if pattern in step_id_lower or pattern in step_role_lower:
                return self.ANALYSIS_TOOLS

        # Check for build patterns
        for pattern in self.BUILD_STEP_PATTERNS:
            if pattern in step_id_lower or pattern in step_role_lower:
                return self.BUILD_TOOLS

        # Default to full tools
        return self.DEFAULT_TOOLS

    def _load_agent_persona(self, agent_key: str) -> Optional[str]:
        """Load agent persona from .claude/agents/<agent_key>.md.

        Strips YAML frontmatter and returns the Markdown body containing
        the agent's identity, behavior, and constraints.

        Args:
            agent_key: The agent identifier (e.g., "code-implementer").

        Returns:
            The agent's persona markdown (without frontmatter), or None if not found.
        """
        if not self.repo_root:
            return None

        agent_path = Path(self.repo_root) / ".claude" / "agents" / f"{agent_key}.md"
        if not agent_path.exists():
            logger.debug("Agent persona not found: %s", agent_path)
            return None

        try:
            content = agent_path.read_text(encoding="utf-8")

            # Strip YAML frontmatter (between --- markers)
            if content.startswith("---"):
                # Find the closing ---
                end_marker = content.find("---", 3)
                if end_marker != -1:
                    # Skip past the closing --- and any immediate newline
                    body_start = end_marker + 3
                    if body_start < len(content) and content[body_start] == "\n":
                        body_start += 1
                    content = content[body_start:]

            return content.strip()

        except (OSError, IOError) as e:
            logger.warning("Failed to load agent persona %s: %s", agent_key, e)
            return None

    async def _run_router_session(
        self,
        handoff_data: Dict[str, Any],
        ctx: StepContext,
        cwd: str,
    ) -> Optional["RoutingSignal"]:
        """Run a lightweight router session to decide the next step.

        This is a fresh, short-lived session that analyzes the handoff
        and produces a routing decision. Uses the ROUTER_PROMPT_TEMPLATE.

        Args:
            handoff_data: The handoff JSON from JIT finalization.
            ctx: Step execution context with routing configuration.
            cwd: Working directory for the session.

        Returns:
            RoutingSignal if routing was determined, None if routing failed.
        """
        from claude_code_sdk import ClaudeCodeOptions, query
        from .types import RoutingDecision, RoutingSignal

        # Extract routing config from context
        routing = ctx.routing or RoutingContext()
        routing_config = ctx.extra.get("routing", {})

        # Build router prompt
        router_prompt = self.ROUTER_PROMPT_TEMPLATE.format(
            handoff_json=json.dumps(handoff_data, indent=2),
            step_id=ctx.step_id,
            flow_key=ctx.flow_key,
            routing_kind=routing_config.get("kind", "linear"),
            routing_next=routing_config.get("next", "null"),
            loop_target=routing_config.get("loop_target", "null"),
            loop_condition_field=routing_config.get("loop_condition_field", "status"),
            loop_success_values=routing_config.get("loop_success_values", ["VERIFIED"]),
            max_iterations=routing_config.get("max_iterations", 3),
            current_iteration=routing.loop_iteration,
        )

        # Router uses minimal options - just needs to analyze and respond
        options = ClaudeCodeOptions(
            permission_mode="bypassPermissions",
        )

        # Collect router response
        router_response = ""

        try:
            logger.debug("Starting router session for step %s", ctx.step_id)

            async for event in query(
                prompt=router_prompt,
                cwd=cwd,
                options=options,
            ):
                # Extract text content from messages
                if hasattr(event, "message"):
                    message = getattr(event, "message", event)
                    content = getattr(message, "content", "")
                    if isinstance(content, list):
                        text_parts = [
                            getattr(b, "text", str(getattr(b, "content", "")))
                            for b in content
                        ]
                        content = "\n".join(text_parts)
                    if content:
                        router_response += content

            logger.debug("Router session complete, parsing response")

            # Parse JSON from response (may be wrapped in markdown)
            json_match = None
            # Try to find JSON block in response
            if "```json" in router_response:
                start = router_response.find("```json") + 7
                end = router_response.find("```", start)
                if end > start:
                    json_match = router_response[start:end].strip()
            elif "```" in router_response:
                start = router_response.find("```") + 3
                end = router_response.find("```", start)
                if end > start:
                    json_match = router_response[start:end].strip()
            else:
                # Try to parse entire response as JSON
                json_match = router_response.strip()

            if not json_match:
                logger.warning("Router response contained no parseable JSON")
                return None

            routing_data = json.loads(json_match)

            # Map decision string to enum
            decision_str = routing_data.get("decision", "advance").lower()
            decision_map = {
                "advance": RoutingDecision.ADVANCE,
                "loop": RoutingDecision.LOOP,
                "terminate": RoutingDecision.TERMINATE,
                "branch": RoutingDecision.BRANCH,
            }
            decision = decision_map.get(decision_str, RoutingDecision.ADVANCE)

            return RoutingSignal(
                decision=decision,
                next_step_id=routing_data.get("next_step_id"),
                route=routing_data.get("route"),
                reason=routing_data.get("reason", ""),
                confidence=float(routing_data.get("confidence", 0.7)),
                needs_human=bool(routing_data.get("needs_human", False)),
            )

        except json.JSONDecodeError as e:
            logger.warning("Failed to parse router response as JSON: %s", e)
            logger.debug("Router response was: %s", router_response[:500])
            return None
        except Exception as e:
            logger.warning("Router session failed: %s", e)
            return None

    def _build_prompt(
        self, ctx: StepContext
    ) -> Tuple[str, Optional[HistoryTruncationInfo], Optional[str]]:
        """Build a context-aware prompt for a step.

        Composes the prompt with agent persona (if available) and step context.
        Returns the persona separately for system_prompt composition.

        Args:
            ctx: Step execution context.

        Returns:
            Tuple of (formatted prompt string, truncation info or None, agent persona or None).
        """
        lines = []

        # Load agent persona for the primary agent
        agent_persona = None
        if ctx.step_agents:
            agent_persona = self._load_agent_persona(ctx.step_agents[0])
            if agent_persona:
                lines.append("# Your Identity")
                lines.append("")
                lines.append(agent_persona)
                lines.append("")
                lines.append("---")
                lines.append("")

        # Flow and step context
        lines.extend([
            f"# Flow: {ctx.flow_title}",
            f"# Step: {ctx.step_id} (Step {ctx.step_index} of {ctx.total_steps})",
            f"# Run ID: {ctx.run_id}",
            "",
            "## Step Role",
            ctx.step_role,
            "",
        ])

        # Agent assignments (for multi-agent steps)
        if ctx.step_agents and len(ctx.step_agents) > 1:
            lines.append("## Assigned Agents")
            for agent in ctx.step_agents:
                lines.append(f"- {agent}")
            lines.append("")

        # Teaching notes (scoped context for this step)
        if ctx.teaching_notes:
            tn = ctx.teaching_notes

            if tn.inputs:
                lines.append("## Expected Inputs")
                lines.append("Read the following files/artifacts for this step:")
                for input_path in tn.inputs:
                    lines.append(f"- {input_path}")
                lines.append("")

            if tn.outputs:
                lines.append("## Expected Outputs")
                lines.append("Produce the following files/artifacts:")
                for output_path in tn.outputs:
                    lines.append(f"- {output_path}")
                lines.append("")

            if tn.emphasizes:
                lines.append("## Key Behaviors")
                lines.append("Focus on these patterns and behaviors:")
                for emphasis in tn.emphasizes:
                    lines.append(f"- {emphasis}")
                lines.append("")

            if tn.constraints:
                lines.append("## Constraints")
                lines.append("Observe these limitations:")
                for constraint in tn.constraints:
                    lines.append(f"- {constraint}")
                lines.append("")

        # RUN_BASE instructions
        lines.extend(
            [
                "## Output Location",
                f"Write outputs to: {ctx.run_base}/",
                "Follow RUN_BASE conventions for all artifacts.",
                "",
            ]
        )

        # Previous step context with priority-aware budget management
        truncation_info: Optional[HistoryTruncationInfo] = None

        if ctx.history:
            lines.append("## Previous Steps Context")
            lines.append("The following steps have already been completed:")
            lines.append("")

            # Get resolved budgets for this step's context
            budgets = self._get_resolved_budgets(ctx.flow_key, ctx.step_id)
            history_budget = budgets.context_budget_chars
            recent_max = budgets.history_max_recent_chars
            older_max = budgets.history_max_older_chars

            # Sort history by priority (CRITICAL first, then HIGH, MEDIUM, LOW)
            # Within same priority, maintain chronological order
            prioritized = prioritize_history(ctx.history)
            total_steps = len(ctx.history)

            # Track which items we include and their priorities
            included_items: List[Tuple[int, Dict[str, Any]]] = []  # (original_idx, item)
            priority_counts: Dict[str, int] = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
            chars_used = 0

            # Most recent step index for determining output limits
            most_recent_idx = total_steps - 1 if total_steps > 0 else -1

            # Process by priority order, including highest-value items first
            for priority, orig_idx, prev in prioritized:
                is_most_recent = orig_idx == most_recent_idx
                step_lines: List[str] = []

                status_emoji = "[OK]" if prev.get("status") == "succeeded" else "[FAIL]"
                priority_label = get_priority_label(priority)
                step_lines.append(f"### Step: {prev.get('step_id')} {status_emoji}")

                if prev.get("output"):
                    output = str(prev.get("output"))
                    # CRITICAL items get full recent budget, others based on recency
                    if priority >= HistoryPriority.CRITICAL:
                        max_chars = recent_max
                    elif is_most_recent:
                        max_chars = recent_max
                    else:
                        max_chars = older_max
                    if len(output) > max_chars:
                        output = output[:max_chars] + "... (truncated)"
                    step_lines.append(f"Output: {output}")

                if prev.get("error"):
                    error = str(prev.get("error"))
                    max_error = 200
                    if len(error) > max_error:
                        error = error[:max_error] + "... (truncated)"
                    step_lines.append(f"Error: {error}")

                step_lines.append("")

                # Calculate chars for this step
                step_text = "\n".join(step_lines)
                step_chars = len(step_text)

                # Check if adding this step would exceed budget
                if chars_used + step_chars > history_budget:
                    # Budget exceeded - skip lower priority items
                    continue

                # Include this item
                included_items.append((orig_idx, prev, step_lines))
                priority_counts[priority_label] += 1
                chars_used += step_chars

            # Sort included items back to chronological order for output
            included_items.sort(key=lambda x: x[0])

            # Build history lines in chronological order
            history_lines: List[str] = []
            for _, _, step_lines in included_items:
                history_lines.extend(step_lines)

            steps_included = len(included_items)

            # Track truncation metadata with priority information
            truncated = steps_included < total_steps
            truncation_info = HistoryTruncationInfo(
                steps_included=steps_included,
                steps_total=total_steps,
                chars_used=chars_used,
                budget_chars=history_budget,
                truncated=truncated,
                priority_aware=True,
                priority_distribution=priority_counts,
            )

            # Add machine-readable truncation warning if we didn't include all steps
            if truncated:
                truncation_warning = truncation_info.truncation_note
                history_lines.insert(0, truncation_warning + "\n")

                # Log for observability
                logger.debug(
                    "History truncation: %s (flow=%s, step=%s)",
                    truncation_warning,
                    ctx.flow_key,
                    ctx.step_id,
                )

            lines.extend(history_lines)

        # Instructions
        lines.extend(
            [
                "## Instructions",
                "1. Execute the step role as described above",
                "2. Use the assigned agent's capabilities and perspective",
                "3. Read any required inputs from previous steps or RUN_BASE",
                "4. Write all outputs to the correct RUN_BASE location",
                "5. Be concise and focused on the specific step",
                "6. When finished, wait for finalization instructions",
                "",
            ]
        )

        return "\n".join(lines), truncation_info, agent_persona

    def run_step(self, ctx: StepContext) -> Tuple[StepResult, Iterable[RunEvent]]:
        """Execute a step using Claude Agent SDK, CLI, or stub mode.

        Mode selection logic:
        1. If mode is "stub" or no execution backend available: use stub
        2. If mode is "cli" and CLI available: use CLI
        3. If mode is "sdk" and SDK available: use SDK
        4. Fallback to stub mode

        Args:
            ctx: Step execution context.

        Returns:
            Tuple of (StepResult, list of RunEvents).
        """
        # Determine execution mode
        if self._mode == "stub":
            logger.debug("ClaudeStepEngine using stub for step %s (explicit stub mode)", ctx.step_id)
            return self._run_step_stub(ctx)

        if self._mode == "cli":
            if self._check_cli_available():
                logger.debug("ClaudeStepEngine using CLI for step %s", ctx.step_id)
                try:
                    return self._run_step_cli(ctx)
                except Exception as e:
                    logger.warning("CLI execution failed for step %s: %s", ctx.step_id, e)
                    return self._make_failed_result(ctx, f"CLI execution failed: {e}")
            else:
                logger.debug(
                    "ClaudeStepEngine CLI not available for step %s, falling back to stub",
                    ctx.step_id,
                )
                return self._run_step_stub(ctx)

        if self._mode == "sdk":
            if self._check_sdk_available():
                logger.debug("ClaudeStepEngine using SDK for step %s", ctx.step_id)
                try:
                    return self._run_step_sdk(ctx)
                except Exception as e:
                    logger.warning("SDK execution failed for step %s: %s", ctx.step_id, e)
                    return self._make_failed_result(ctx, f"SDK execution failed: {e}")
            else:
                logger.debug(
                    "ClaudeStepEngine SDK not available for step %s, falling back to stub",
                    ctx.step_id,
                )
                return self._run_step_stub(ctx)

        # Default: try SDK, then CLI, then stub
        if self._check_sdk_available():
            logger.debug("ClaudeStepEngine using SDK for step %s (auto-detected)", ctx.step_id)
            try:
                return self._run_step_sdk(ctx)
            except Exception as e:
                logger.warning("SDK execution failed for step %s: %s", ctx.step_id, e)
                return self._make_failed_result(ctx, f"SDK execution failed: {e}")

        if self._check_cli_available():
            logger.debug("ClaudeStepEngine using CLI for step %s (auto-detected)", ctx.step_id)
            try:
                return self._run_step_cli(ctx)
            except Exception as e:
                logger.warning("CLI execution failed for step %s: %s", ctx.step_id, e)
                return self._make_failed_result(ctx, f"CLI execution failed: {e}")

        logger.debug("ClaudeStepEngine using stub for step %s (no execution backend)", ctx.step_id)
        return self._run_step_stub(ctx)

    def _make_failed_result(
        self, ctx: StepContext, error: str
    ) -> Tuple[StepResult, Iterable[RunEvent]]:
        """Create a failed result for error cases."""
        return StepResult(
            step_id=ctx.step_id,
            status="failed",
            output="",
            error=error,
            duration_ms=0,
        ), []

    def _run_step_stub(self, ctx: StepContext) -> Tuple[StepResult, Iterable[RunEvent]]:
        """Execute a step in stub mode (no real API calls).

        Args:
            ctx: Step execution context.

        Returns:
            Tuple of (StepResult, list of RunEvents).
        """
        start_time = datetime.now(timezone.utc)
        agent_key = ctx.step_agents[0] if ctx.step_agents else "unknown"

        # Create directories for transcripts and receipts using path helpers
        ensure_llm_dir(ctx.run_base)
        ensure_receipts_dir(ctx.run_base)

        # Generate paths using path helpers
        t_path = make_transcript_path(ctx.run_base, ctx.step_id, agent_key, "claude")
        r_path = make_receipt_path(ctx.run_base, ctx.step_id, agent_key)

        # Build prompt to get truncation info (even in stub mode for consistency)
        _, truncation_info, _ = self._build_prompt(ctx)

        # Write transcript JSONL (stub messages)
        transcript_messages = [
            {
                "timestamp": start_time.isoformat() + "Z",
                "role": "system",
                "content": f"Executing step {ctx.step_id} with agent {agent_key}",
            },
            {
                "timestamp": start_time.isoformat() + "Z",
                "role": "user",
                "content": f"Step role: {ctx.step_role}",
            },
            {
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                "role": "assistant",
                "content": f"[STUB] Completed step {ctx.step_id}. "
                f"In production, this would contain the actual Claude response.",
            },
        ]
        with t_path.open("w", encoding="utf-8") as f:
            for msg in transcript_messages:
                f.write(json.dumps(msg) + "\n")

        end_time = datetime.now(timezone.utc)
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        # Write receipt JSON with mode and provider fields
        receipt = {
            "engine": self.engine_id,
            "mode": "stub",
            "provider": self._provider or "none",
            "model": "claude-stub",
            "step_id": ctx.step_id,
            "flow_key": ctx.flow_key,
            "run_id": ctx.run_id,
            "agent_key": agent_key,
            "started_at": start_time.isoformat() + "Z",
            "completed_at": end_time.isoformat() + "Z",
            "duration_ms": duration_ms,
            "status": "succeeded",
            "tokens": {"prompt": 0, "completion": 0, "total": 0},
            "transcript_path": str(t_path.relative_to(ctx.run_base)),
        }
        # Add context truncation info if provided
        if truncation_info:
            receipt["context_truncation"] = truncation_info.to_dict()

        with r_path.open("w", encoding="utf-8") as f:
            json.dump(receipt, f, indent=2)

        # Emit events for observability
        events: List[RunEvent] = [
            RunEvent(
                run_id=ctx.run_id,
                ts=start_time,
                kind="log",
                flow_key=ctx.flow_key,
                step_id=ctx.step_id,
                agent_key=agent_key,
                payload={
                    "message": f"ClaudeStepEngine stub executed step {ctx.step_id}",
                    "engine_id": self.engine_id,
                    "mode": "stub",
                    "provider": self._provider or "none",
                    "transcript_path": str(t_path.relative_to(ctx.run_base)),
                    "receipt_path": str(r_path.relative_to(ctx.run_base)),
                },
            )
        ]

        result = StepResult(
            step_id=ctx.step_id,
            status="succeeded",
            output=f"[STUB:{self.engine_id}] Step {ctx.step_id} completed successfully",
            duration_ms=duration_ms,
            artifacts={
                "transcript_path": str(t_path),
                "receipt_path": str(r_path),
            },
        )

        return result, events

    def _run_step_cli(self, ctx: StepContext) -> Tuple[StepResult, Iterable[RunEvent]]:
        """Execute a step using the Claude CLI.

        Uses `claude --output-format stream-json` to execute the step
        and captures JSONL output for transcripts.

        Args:
            ctx: Step execution context.

        Returns:
            Tuple of (StepResult, list of RunEvents).
        """
        events: List[RunEvent] = []
        start_time = datetime.now(timezone.utc)
        agent_key = ctx.step_agents[0] if ctx.step_agents else "unknown"

        # Create directories for transcripts and receipts
        ensure_llm_dir(ctx.run_base)
        ensure_receipts_dir(ctx.run_base)

        # Generate paths
        t_path = make_transcript_path(ctx.run_base, ctx.step_id, agent_key, "claude")
        r_path = make_receipt_path(ctx.run_base, ctx.step_id, agent_key)

        # Build prompt (returns tuple with truncation info and persona)
        prompt, truncation_info, _ = self._build_prompt(ctx)

        # Build CLI command
        args = [
            self._cli_cmd,
            "-p",  # Print mode (non-interactive)
            "--output-format",
            "stream-json",
        ]

        cmd = " ".join(shlex.quote(a) for a in args)

        # Set working directory
        cwd = str(ctx.repo_root) if ctx.repo_root else str(Path.cwd())

        # Execute CLI
        process = subprocess.Popen(
            cmd,
            cwd=cwd,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Collect raw events for transcript and track assistant content
        raw_events: List[Dict[str, Any]] = []
        full_assistant_text: List[str] = []
        token_counts: Dict[str, int] = {"prompt": 0, "completion": 0, "total": 0}
        model_name = "claude-sonnet-4-20250514"  # Default model

        # Send prompt via stdin
        stdout_data, stderr_data = process.communicate(input=prompt, timeout=300)

        # Parse JSONL output
        if stdout_data:
            for line in stdout_data.strip().split("\n"):
                line = line.strip()
                if not line:
                    continue

                try:
                    event_data = json.loads(line)
                    raw_events.append(event_data)

                    # Map event types to RunEvents
                    event_type = event_data.get("type", "unknown")

                    if event_type == "message":
                        role = event_data.get("role", "assistant")
                        content = event_data.get("content", "")
                        if role == "assistant" and content:
                            full_assistant_text.append(content)

                        event = RunEvent(
                            run_id=ctx.run_id,
                            ts=datetime.now(timezone.utc),
                            kind="assistant_message" if role == "assistant" else "user_message",
                            flow_key=ctx.flow_key,
                            step_id=ctx.step_id,
                            agent_key=agent_key,
                            payload={"role": role, "content": content[:500]},
                        )
                        events.append(event)

                    elif event_type == "tool_use":
                        tool_name = event_data.get("tool") or event_data.get("name", "unknown")
                        tool_input = event_data.get("input") or event_data.get("args", {})
                        events.append(
                            RunEvent(
                                run_id=ctx.run_id,
                                ts=datetime.now(timezone.utc),
                                kind="tool_start",
                                flow_key=ctx.flow_key,
                                step_id=ctx.step_id,
                                agent_key=agent_key,
                                payload={"tool": tool_name, "input": str(tool_input)[:200]},
                            )
                        )

                    elif event_type == "tool_result":
                        tool_name = event_data.get("tool") or event_data.get("name", "unknown")
                        result = event_data.get("output") or event_data.get("result", "")
                        success = event_data.get("success", True)
                        events.append(
                            RunEvent(
                                run_id=ctx.run_id,
                                ts=datetime.now(timezone.utc),
                                kind="tool_end",
                                flow_key=ctx.flow_key,
                                step_id=ctx.step_id,
                                agent_key=agent_key,
                                payload={
                                    "tool": tool_name,
                                    "success": success,
                                    "output": str(result)[:200],
                                },
                            )
                        )

                    elif event_type == "result":
                        # Extract token usage if available
                        usage = event_data.get("usage", {})
                        if usage:
                            token_counts["prompt"] = usage.get("input_tokens", 0)
                            token_counts["completion"] = usage.get("output_tokens", 0)
                            token_counts["total"] = (
                                token_counts["prompt"] + token_counts["completion"]
                            )
                        # Extract model if available
                        if event_data.get("model"):
                            model_name = event_data["model"]

                except json.JSONDecodeError:
                    # Log as text event
                    raw_events.append({"type": "text", "message": line})
                    events.append(
                        RunEvent(
                            run_id=ctx.run_id,
                            ts=datetime.now(timezone.utc),
                            kind="log",
                            flow_key=ctx.flow_key,
                            step_id=ctx.step_id,
                            payload={"message": line},
                        )
                    )

        end_time = datetime.now(timezone.utc)
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        # Determine status
        if process.returncode != 0:
            status = "failed"
            error = stderr_data[:500] if stderr_data else f"Exit code {process.returncode}"
        else:
            status = "succeeded"
            error = None

        # Write transcript JSONL
        with t_path.open("w", encoding="utf-8") as f:
            for event in raw_events:
                if "timestamp" not in event:
                    event["timestamp"] = datetime.now(timezone.utc).isoformat() + "Z"
                f.write(json.dumps(event) + "\n")

        # Write receipt JSON
        receipt = {
            "engine": self.engine_id,
            "mode": "cli",
            "provider": self._provider,
            "model": model_name,
            "step_id": ctx.step_id,
            "flow_key": ctx.flow_key,
            "run_id": ctx.run_id,
            "agent_key": agent_key,
            "started_at": start_time.isoformat() + "Z",
            "completed_at": end_time.isoformat() + "Z",
            "duration_ms": duration_ms,
            "status": status,
            "tokens": token_counts,
            "transcript_path": str(t_path.relative_to(ctx.run_base)),
        }
        if error:
            receipt["error"] = error
        # Add context truncation info if provided
        if truncation_info:
            receipt["context_truncation"] = truncation_info.to_dict()

        with r_path.open("w", encoding="utf-8") as f:
            json.dump(receipt, f, indent=2)

        # Build output text
        combined_text = "".join(full_assistant_text)
        if len(combined_text) > 2000:
            output_text = combined_text[:2000] + "... (truncated)"
        elif combined_text:
            output_text = combined_text
        else:
            output_text = f"Step {ctx.step_id} completed via CLI. Events: {len(raw_events)}"

        result = StepResult(
            step_id=ctx.step_id,
            status=status,
            output=output_text,
            error=error,
            duration_ms=duration_ms,
            artifacts={
                "transcript_path": str(t_path),
                "receipt_path": str(r_path),
            },
        )

        return result, events

    def _run_step_sdk(self, ctx: StepContext) -> Tuple[StepResult, Iterable[RunEvent]]:
        """Execute a step using the Claude Agent SDK.

        Args:
            ctx: Step execution context.

        Returns:
            Tuple of (StepResult, list of RunEvents).
        """
        import asyncio

        # Run the async SDK call in a sync wrapper
        return asyncio.get_event_loop().run_until_complete(self._run_step_sdk_async(ctx))

    async def _run_step_sdk_async(
        self, ctx: StepContext
    ) -> Tuple[StepResult, Iterable[RunEvent]]:
        """Execute a step using the Claude Agent SDK (async implementation).

        Args:
            ctx: Step execution context.

        Returns:
            Tuple of (StepResult, list of RunEvents).
        """
        from claude_code_sdk import ClaudeCodeOptions, query

        start_time = datetime.now(timezone.utc)
        agent_key = ctx.step_agents[0] if ctx.step_agents else "unknown"
        events: List[RunEvent] = []

        # Create directories for transcripts and receipts
        ensure_llm_dir(ctx.run_base)
        ensure_receipts_dir(ctx.run_base)

        # Generate paths
        t_path = make_transcript_path(ctx.run_base, ctx.step_id, agent_key, "claude")
        r_path = make_receipt_path(ctx.run_base, ctx.step_id, agent_key)

        # Build prompt (returns tuple with truncation info and persona)
        prompt, truncation_info, agent_persona = self._build_prompt(ctx)

        # Set up working directory
        cwd = str(ctx.repo_root) if ctx.repo_root else str(Path.cwd())

        # Prepare options with HIGH TRUST configuration
        # - permission_mode="bypassPermissions": No interactive approval needed
        # - No allowed_tools restriction: Full access to all tools
        # - system_prompt uses preset + persona append for identity injection
        options = ClaudeCodeOptions(
            permission_mode="bypassPermissions",
            # Note: We pass persona in the user prompt rather than system_prompt
            # because the SDK's preset handling is more reliable there
        )

        # Compute handoff path for JIT finalization
        handoff_dir = ctx.run_base / "handoff"
        handoff_path = handoff_dir / f"{ctx.step_id}.draft.json"

        # Record step start in stats DB
        if self._stats_db:
            try:
                self._stats_db.record_step_start(
                    run_id=ctx.run_id,
                    flow_key=ctx.flow_key,
                    step_id=ctx.step_id,
                    step_index=ctx.step_index,
                    agent_key=agent_key,
                )
            except Exception as db_err:
                logger.debug("Failed to record step start: %s", db_err)

        # Collect transcript entries and assistant output
        raw_events: List[Dict[str, Any]] = []
        full_assistant_text: List[str] = []
        token_counts: Dict[str, int] = {"prompt": 0, "completion": 0, "total": 0}
        model_name = "claude-sonnet-4-20250514"  # Default model

        try:
            # Execute the query
            async for event in query(
                prompt=prompt,
                cwd=cwd,
                options=options,
            ):
                now = datetime.now(timezone.utc)
                event_dict: Dict[str, Any] = {"timestamp": now.isoformat() + "Z"}

                # Handle different event types
                event_type = getattr(event, "type", None) or type(event).__name__

                if event_type == "AssistantMessageEvent" or hasattr(event, "message"):
                    # Message event
                    message = getattr(event, "message", event)
                    role = getattr(message, "role", "assistant")
                    content = getattr(message, "content", "")

                    # Handle content blocks
                    if isinstance(content, list):
                        text_parts = []
                        for block in content:
                            if hasattr(block, "text"):
                                text_parts.append(block.text)
                            elif hasattr(block, "content"):
                                text_parts.append(str(block.content))
                        content = "\n".join(text_parts)

                    event_dict["role"] = role
                    event_dict["content"] = content
                    event_dict["type"] = "message"

                    if role == "assistant" and content:
                        full_assistant_text.append(content)

                    # Map to RunEvent
                    events.append(
                        RunEvent(
                            run_id=ctx.run_id,
                            ts=now,
                            kind="assistant_message" if role == "assistant" else "user_message",
                            flow_key=ctx.flow_key,
                            step_id=ctx.step_id,
                            agent_key=agent_key,
                            payload={"role": role, "content": content[:500]},
                        )
                    )

                elif event_type == "ToolUseEvent" or hasattr(event, "tool_name"):
                    # Tool use event
                    tool_name = getattr(event, "tool_name", getattr(event, "name", "unknown"))
                    tool_input = getattr(event, "input", getattr(event, "args", {}))

                    event_dict["type"] = "tool_use"
                    event_dict["tool"] = tool_name
                    event_dict["input"] = tool_input

                    events.append(
                        RunEvent(
                            run_id=ctx.run_id,
                            ts=now,
                            kind="tool_start",
                            flow_key=ctx.flow_key,
                            step_id=ctx.step_id,
                            agent_key=agent_key,
                            payload={"tool": tool_name, "input": str(tool_input)[:200]},
                        )
                    )

                elif event_type == "ToolResultEvent" or hasattr(event, "tool_result"):
                    # Tool result event
                    result = getattr(event, "tool_result", getattr(event, "result", ""))
                    success = getattr(event, "success", True)
                    tool_name = getattr(event, "tool_name", "unknown")

                    event_dict["type"] = "tool_result"
                    event_dict["tool"] = tool_name
                    event_dict["success"] = success
                    event_dict["output"] = str(result)[:500]

                    events.append(
                        RunEvent(
                            run_id=ctx.run_id,
                            ts=now,
                            kind="tool_end",
                            flow_key=ctx.flow_key,
                            step_id=ctx.step_id,
                            agent_key=agent_key,
                            payload={
                                "tool": tool_name,
                                "success": success,
                                "output": str(result)[:200],
                            },
                        )
                    )

                    # Record tool call in stats DB
                    if self._stats_db:
                        try:
                            # Extract file path for file operations
                            target_path = None
                            if tool_name in ("Edit", "Write", "Read"):
                                target_path = str(getattr(event, "file_path", ""))[:500]

                            self._stats_db.record_tool_call(
                                run_id=ctx.run_id,
                                step_id=ctx.step_id,
                                tool_name=tool_name,
                                phase="work",
                                success=success,
                                target_path=target_path,
                            )
                        except Exception as db_err:
                            logger.debug("Failed to record tool call: %s", db_err)

                elif event_type == "ResultEvent" or hasattr(event, "result"):
                    # Final result event
                    result = getattr(event, "result", event)
                    event_dict["type"] = "result"

                    # Extract token usage if available
                    usage = getattr(result, "usage", None)
                    if usage:
                        token_counts["prompt"] = getattr(usage, "input_tokens", 0)
                        token_counts["completion"] = getattr(usage, "output_tokens", 0)
                        token_counts["total"] = (
                            token_counts["prompt"] + token_counts["completion"]
                        )
                        event_dict["usage"] = token_counts

                    # Extract model if available
                    result_model = getattr(result, "model", None)
                    if result_model:
                        model_name = result_model

                else:
                    # Generic event handling
                    event_dict["type"] = event_type
                    if hasattr(event, "__dict__"):
                        for k, v in event.__dict__.items():
                            if not k.startswith("_"):
                                try:
                                    json.dumps(v)  # Check if serializable
                                    event_dict[k] = v
                                except (TypeError, ValueError):
                                    event_dict[k] = str(v)

                raw_events.append(event_dict)

            # ===== JIT FINALIZATION =====
            # Work session complete. Now inject finalization prompt to extract state.
            logger.debug("Work session complete for step %s, starting JIT finalization", ctx.step_id)

            # Ensure handoff directory exists
            handoff_dir.mkdir(parents=True, exist_ok=True)

            # Build finalization prompt
            finalization_prompt = self.JIT_FINALIZATION_PROMPT.format(
                handoff_path=str(handoff_path),
                step_id=ctx.step_id,
                flow_key=ctx.flow_key,
                run_id=ctx.run_id,
            )

            # Add context about what was accomplished
            work_summary = "".join(full_assistant_text)
            if len(work_summary) > 4000:
                work_summary = work_summary[:4000] + "... (truncated)"

            finalization_with_context = f"""
## Work Session Summary
{work_summary}

{finalization_prompt}
"""

            # Execute finalization query (same options, fresh prompt)
            finalization_events: List[Dict[str, Any]] = []
            try:
                async for event in query(
                    prompt=finalization_with_context,
                    cwd=cwd,
                    options=options,
                ):
                    now = datetime.now(timezone.utc)
                    event_dict = {"timestamp": now.isoformat() + "Z", "phase": "finalization"}

                    event_type = getattr(event, "type", None) or type(event).__name__

                    if event_type == "AssistantMessageEvent" or hasattr(event, "message"):
                        message = getattr(event, "message", event)
                        content = getattr(message, "content", "")
                        if isinstance(content, list):
                            text_parts = [getattr(b, "text", str(getattr(b, "content", ""))) for b in content]
                            content = "\n".join(text_parts)
                        event_dict["type"] = "message"
                        event_dict["content"] = content[:500]

                    elif event_type == "ToolUseEvent" or hasattr(event, "tool_name"):
                        tool_name = getattr(event, "tool_name", getattr(event, "name", "unknown"))
                        event_dict["type"] = "tool_use"
                        event_dict["tool"] = tool_name

                    elif event_type == "ToolResultEvent" or hasattr(event, "tool_result"):
                        event_dict["type"] = "tool_result"
                        event_dict["success"] = getattr(event, "success", True)

                    else:
                        event_dict["type"] = event_type

                    finalization_events.append(event_dict)
                    raw_events.append(event_dict)

                logger.debug("JIT finalization complete for step %s", ctx.step_id)

            except Exception as fin_error:
                logger.warning("JIT finalization failed for step %s: %s", ctx.step_id, fin_error)
                raw_events.append({
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                    "phase": "finalization",
                    "type": "error",
                    "error": str(fin_error),
                })

            # ===== HANDOFF EXTRACTION =====
            # Try to read the handoff file written by the agent
            handoff_data: Optional[Dict[str, Any]] = None
            if handoff_path.exists():
                try:
                    handoff_data = json.loads(handoff_path.read_text(encoding="utf-8"))
                    logger.debug("Handoff extracted from %s: status=%s", handoff_path, handoff_data.get("status"))
                except (json.JSONDecodeError, OSError) as e:
                    logger.warning("Failed to parse handoff file %s: %s", handoff_path, e)
            else:
                logger.warning("Handoff file not created by agent: %s", handoff_path)

            # ===== AGENTIC ROUTING =====
            # Run a lightweight router session to decide the next step
            routing_signal: Optional["RoutingSignal"] = None
            if handoff_data:
                try:
                    routing_signal = await self._run_router_session(
                        handoff_data=handoff_data,
                        ctx=ctx,
                        cwd=cwd,
                    )
                    if routing_signal:
                        logger.debug(
                            "Router decision for step %s: %s -> %s (confidence=%.2f)",
                            ctx.step_id,
                            routing_signal.decision.value,
                            routing_signal.next_step_id,
                            routing_signal.confidence,
                        )
                        # Record routing event
                        raw_events.append({
                            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                            "phase": "routing",
                            "type": "routing_decision",
                            "decision": routing_signal.decision.value,
                            "next_step_id": routing_signal.next_step_id,
                            "confidence": routing_signal.confidence,
                            "reason": routing_signal.reason,
                        })
                except Exception as route_error:
                    logger.warning("Router session failed for step %s: %s", ctx.step_id, route_error)
                    raw_events.append({
                        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                        "phase": "routing",
                        "type": "error",
                        "error": str(route_error),
                    })

            status = "succeeded"
            error = None

        except Exception as e:
            logger.warning("SDK query failed for step %s: %s", ctx.step_id, e)
            status = "failed"
            error = str(e)
            handoff_data = None  # Ensure defined for receipt/result building
            routing_signal = None  # Ensure defined for receipt/result building
            raw_events.append(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                    "type": "error",
                    "error": str(e),
                }
            )

        end_time = datetime.now(timezone.utc)
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        # Write transcript JSONL
        with t_path.open("w", encoding="utf-8") as f:
            for event in raw_events:
                f.write(json.dumps(event) + "\n")

        # Write receipt JSON with mode and provider fields
        receipt = {
            "engine": self.engine_id,
            "mode": "sdk",
            "provider": self._provider or "anthropic",
            "model": model_name,
            "step_id": ctx.step_id,
            "flow_key": ctx.flow_key,
            "run_id": ctx.run_id,
            "agent_key": agent_key,
            "started_at": start_time.isoformat() + "Z",
            "completed_at": end_time.isoformat() + "Z",
            "duration_ms": duration_ms,
            "status": status,
            "tokens": token_counts,
            "transcript_path": str(t_path.relative_to(ctx.run_base)),
            "permission_mode": "bypassPermissions",  # High-trust mode
            "jit_finalization": handoff_path.exists(),
        }
        # Add context truncation info if provided
        if truncation_info:
            receipt["context_truncation"] = truncation_info.to_dict()

        # Add handoff data if extracted
        if handoff_data:
            receipt["handoff"] = {
                "status": handoff_data.get("status"),
                "proposed_next_step": handoff_data.get("proposed_next_step"),
                "confidence": handoff_data.get("confidence"),
                "artifacts": handoff_data.get("artifacts", {}),
            }
            # Use handoff status if available
            handoff_status = handoff_data.get("status", "").upper()
            if handoff_status in ("VERIFIED", "UNVERIFIED", "PARTIAL", "BLOCKED"):
                receipt["handoff_status"] = handoff_status

        # Add routing signal if determined
        if routing_signal:
            receipt["routing_signal"] = {
                "decision": routing_signal.decision.value,
                "next_step_id": routing_signal.next_step_id,
                "route": routing_signal.route,
                "reason": routing_signal.reason,
                "confidence": routing_signal.confidence,
                "needs_human": routing_signal.needs_human,
            }

        with r_path.open("w", encoding="utf-8") as f:
            json.dump(receipt, f, indent=2)

        # Build output text - prefer handoff summary if available
        if handoff_data and handoff_data.get("summary"):
            output_text = handoff_data["summary"]
            if len(output_text) > 2000:
                output_text = output_text[:2000] + "... (truncated)"
        else:
            combined_text = "".join(full_assistant_text)
            if len(combined_text) > 2000:
                output_text = combined_text[:2000] + "... (truncated)"
            elif combined_text:
                output_text = combined_text
            else:
                output_text = f"Step {ctx.step_id} completed. Events: {len(raw_events)}"

        # Build artifacts dict including handoff and routing
        artifacts = {
            "transcript_path": str(t_path),
            "receipt_path": str(r_path),
        }
        if handoff_path.exists():
            artifacts["handoff_path"] = str(handoff_path)
        if handoff_data and handoff_data.get("artifacts"):
            artifacts["step_artifacts"] = handoff_data["artifacts"]
        if routing_signal:
            artifacts["routing_signal"] = {
                "decision": routing_signal.decision.value,
                "next_step_id": routing_signal.next_step_id,
                "confidence": routing_signal.confidence,
                "needs_human": routing_signal.needs_human,
            }

        # Record step end in stats DB
        if self._stats_db:
            try:
                self._stats_db.record_step_end(
                    run_id=ctx.run_id,
                    flow_key=ctx.flow_key,
                    step_id=ctx.step_id,
                    status=status,
                    duration_ms=duration_ms,
                    prompt_tokens=token_counts.get("prompt", 0),
                    completion_tokens=token_counts.get("completion", 0),
                    handoff_status=handoff_data.get("status") if handoff_data else None,
                    routing_decision=routing_signal.decision.value if routing_signal else None,
                    routing_next_step=routing_signal.next_step_id if routing_signal else None,
                    routing_confidence=routing_signal.confidence if routing_signal else None,
                    error_message=error,
                )
            except Exception as db_err:
                logger.debug("Failed to record step end: %s", db_err)

        result = StepResult(
            step_id=ctx.step_id,
            status=status,
            output=output_text,
            error=error,
            duration_ms=duration_ms,
            artifacts=artifacts,
        )

        return result, events


# =============================================================================
# Engine Factory
# =============================================================================


def get_step_engine(
    engine_id: str,
    repo_root: Path,
    mode: Optional[str] = None,
) -> StepEngine:
    """Get a step engine by ID with optional mode override.

    This factory function provides a centralized way to instantiate engines
    based on configuration from runtime.yaml and environment variables.

    Engine IDs:
    - "gemini-step" or "gemini": GeminiStepEngine
    - "claude-step" or "claude": ClaudeStepEngine

    Args:
        engine_id: Engine identifier ("gemini-step", "claude-step", etc.)
        repo_root: Repository root path.
        mode: Optional mode override ("stub", "sdk", "cli").
              If None, reads from config/environment.

    Returns:
        Configured StepEngine instance.

    Raises:
        ValueError: If engine_id is not recognized.

    Example:
        >>> engine = get_step_engine("claude-step", Path.cwd(), mode="cli")
        >>> result, events = engine.run_step(ctx)
    """
    engine_id_lower = engine_id.lower()

    if engine_id_lower in ("gemini-step", "gemini"):
        return GeminiStepEngine(repo_root)

    if engine_id_lower in ("claude-step", "claude"):
        return ClaudeStepEngine(repo_root, mode=mode)

    raise ValueError(
        f"Unknown engine ID: {engine_id}. "
        f"Valid options: gemini-step, claude-step"
    )


def list_available_engines() -> List[Dict[str, Any]]:
    """List available step engines with their configuration.

    Returns:
        List of dicts with engine metadata:
        - id: Engine identifier
        - label: Human-readable label
        - modes: Available modes for this engine
        - default_mode: Default mode from config
    """
    from swarm.config.runtime_config import get_engine_mode, get_engine_provider

    return [
        {
            "id": "gemini-step",
            "label": "Gemini CLI",
            "modes": ["stub", "cli"],
            "default_mode": get_engine_mode("gemini"),
            "provider": "gemini",
        },
        {
            "id": "claude-step",
            "label": "Claude Agent SDK/CLI",
            "modes": ["stub", "sdk", "cli"],
            "default_mode": get_engine_mode("claude"),
            "provider": get_engine_provider("claude"),
        },
    ]
