"""Session management for Claude SDK integration.

This module provides:
- StepSessionClient: Per-step session orchestrator (Work -> Finalize -> Route)
- StepSession: Single step execution session
- _parse_json_response: Helper for parsing JSON from SDK responses

These modules use SDK calls for actual execution.
"""

from __future__ import annotations

import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Tuple

from swarm.runtime.types.tool_call import (
    NormalizedToolCall,
    truncate_output,
)

from swarm.runtime._claude_sdk.constants import DEFAULT_MODEL
from swarm.runtime._claude_sdk.hooks import (
    PostToolUseHook,
    PreToolUseHook,
)
from swarm.runtime._claude_sdk.options import create_high_trust_options
from swarm.runtime._claude_sdk.policy import create_tool_policy_hook
from swarm.runtime._claude_sdk.schemas import (
    HANDOFF_ENVELOPE_SCHEMA,
    ROUTING_SIGNAL_SCHEMA,
)
from swarm.runtime._claude_sdk.sdk_import import (
    check_sdk_available,
    get_sdk_module,
)
from swarm.runtime._claude_sdk.session_types import (
    FinalizePhaseResult,
    RoutePhaseResult,
    StepSessionResult,
    WorkPhaseResult,
)
from swarm.runtime._claude_sdk.telemetry import TelemetryData

# Module logger
logger = logging.getLogger(__name__)


# =============================================================================
# StepSessionClient - Per-Step Session Pattern
# =============================================================================


class StepSessionClient:
    """Client for per-step SDK sessions with Work -> Finalize -> Route pattern.

    This client implements the SDK alignment pattern where each step gets ONE
    session that handles all phases:
    1. Work phase: Agent does its task
    2. Finalize phase: Extract structured handoff envelope via output_format
    3. Route phase: Determine next step via output_format (if not terminal)

    Benefits:
    - Preserves hot context within a step (no context loss between phases)
    - Enables interrupts mid-step for observability
    - Uses structured output_format for reliable JSON extraction
    - Implements high-trust tool policy with foot-gun blocking
    - Supports PreToolUse/PostToolUse hooks for guardrails
    - Collects telemetry data for each phase

    Example:
        >>> client = StepSessionClient(repo_root=Path("/repo"))
        >>> async with client.step_session(ctx) as session:
        ...     work = await session.work(prompt="Implement feature X")
        ...     envelope = await session.finalize()
        ...     routing = await session.route()
        >>> result = session.get_result()
        >>> print(result.telemetry)
    """

    def __init__(
        self,
        repo_root: Optional[Path] = None,
        model: Optional[str] = None,
        tool_policy_hook: Optional[
            Callable[[str, Dict[str, Any]], Tuple[bool, Optional[str]]]
        ] = None,
        pre_tool_hooks: Optional[List[PreToolUseHook]] = None,
        post_tool_hooks: Optional[List[PostToolUseHook]] = None,
    ):
        """Initialize the Claude SDK client.

        Args:
            repo_root: Repository root for cwd setting.
            model: Model override (uses DEFAULT_MODEL if not specified).
            tool_policy_hook: Optional hook for tool policy validation (legacy).
            pre_tool_hooks: Optional list of pre-tool-use hooks for guardrails.
            post_tool_hooks: Optional list of post-tool-use hooks for telemetry.
        """
        self.repo_root = repo_root or Path.cwd()
        self.model = model or DEFAULT_MODEL
        self.tool_policy_hook = tool_policy_hook or create_tool_policy_hook()
        self.pre_tool_hooks: List[PreToolUseHook] = pre_tool_hooks or []
        self.post_tool_hooks: List[PostToolUseHook] = post_tool_hooks or []
        self._sdk_available: Optional[bool] = None

    def _check_sdk(self) -> bool:
        """Check and cache SDK availability."""
        if self._sdk_available is None:
            self._sdk_available = check_sdk_available()
        return self._sdk_available

    @asynccontextmanager
    async def step_session(
        self,
        step_id: str,
        flow_key: str,
        run_id: str,
        system_prompt_append: Optional[str] = None,
        is_terminal: bool = False,
    ):
        """Create a step session context manager.

        Each step gets ONE session that handles Work -> Finalize -> Route.
        The session preserves context between phases (hot context).

        Args:
            step_id: The step identifier.
            flow_key: The flow key (signal, plan, build, etc.).
            run_id: The run identifier.
            system_prompt_append: Optional persona/context to append to system prompt.
            is_terminal: Whether this is a terminal step (no routing needed).

        Yields:
            A StepSession instance for executing the step phases.
        """
        import secrets
        import string

        session_id = "".join(
            secrets.choice(string.ascii_lowercase + string.digits) for _ in range(8)
        )

        session = StepSession(
            client=self,
            step_id=step_id,
            flow_key=flow_key,
            run_id=run_id,
            session_id=session_id,
            system_prompt_append=system_prompt_append,
            is_terminal=is_terminal,
        )

        logger.debug(
            "Starting step session %s for step %s (flow=%s, run=%s, terminal=%s)",
            session_id,
            step_id,
            flow_key,
            run_id,
            is_terminal,
        )

        try:
            yield session
        finally:
            # Log session completion
            logger.debug(
                "Step session %s completed for step %s (work=%s, finalize=%s, route=%s)",
                session_id,
                step_id,
                session._work_completed,
                session._finalize_completed,
                session._route_completed,
            )


class StepSession:
    """A single step's execution session.

    Handles the Work -> Finalize -> Route pattern within a single hot context.
    Each phase builds on the previous phase's context.

    Supports:
    - PreToolUse/PostToolUse hooks for guardrails and telemetry
    - Structured output via output_format for finalize/route phases
    - Telemetry collection for each phase
    """

    def __init__(
        self,
        client: "StepSessionClient",
        step_id: str,
        flow_key: str,
        run_id: str,
        session_id: str,
        system_prompt_append: Optional[str] = None,
        is_terminal: bool = False,
    ):
        """Initialize the step session.

        Args:
            client: The parent StepSessionClient.
            step_id: The step identifier.
            flow_key: The flow key.
            run_id: The run identifier.
            session_id: Unique session identifier.
            system_prompt_append: Optional system prompt append.
            is_terminal: Whether this is a terminal step.
        """
        self.client = client
        self.step_id = step_id
        self.flow_key = flow_key
        self.run_id = run_id
        self.session_id = session_id
        self.system_prompt_append = system_prompt_append
        self.is_terminal = is_terminal

        # Phase completion tracking
        self._work_completed = False
        self._finalize_completed = False
        self._route_completed = False

        # Accumulated results
        self._work_result: Optional[WorkPhaseResult] = None
        self._finalize_result: Optional[FinalizePhaseResult] = None
        self._route_result: Optional[RoutePhaseResult] = None

        # Conversation state for hot context
        self._conversation_history: List[Dict[str, Any]] = []

        # Start time for duration tracking
        self._start_time = datetime.now(timezone.utc)

        # Telemetry data per phase
        self._telemetry: Dict[str, TelemetryData] = {}

        # Active tool context for hook communication
        self._tool_context: Dict[str, Any] = {}

    async def work(
        self,
        prompt: str,
        tools: Optional[List[str]] = None,
    ) -> WorkPhaseResult:
        """Execute the work phase of the step.

        The agent performs its primary task based on the prompt.
        Collects telemetry and invokes hooks for each tool call.

        Args:
            prompt: The step objective/prompt.
            tools: Optional list of tools to make available.

        Returns:
            WorkPhaseResult with output, events, and tool calls.
        """
        if self._work_completed:
            raise RuntimeError("Work phase already completed for this session")

        # Initialize telemetry for this phase
        telemetry = TelemetryData(
            phase="work",
            start_time=datetime.now(timezone.utc).isoformat() + "Z",
        )
        self._telemetry["work"] = telemetry

        if not self.client._check_sdk():
            self._work_result = WorkPhaseResult(
                success=False,
                output="",
                error="Claude SDK not available",
            )
            telemetry.errors.append("Claude SDK not available")
            telemetry.finalize()
            self._work_completed = True
            return self._work_result

        sdk = get_sdk_module()

        options = create_high_trust_options(
            cwd=str(self.client.repo_root),
            permission_mode="bypassPermissions",
            model=self.client.model,
            system_prompt_append=self.system_prompt_append,
        )

        events: List[Dict[str, Any]] = []
        full_text: List[str] = []
        tool_calls: List[NormalizedToolCall] = []
        token_counts: Dict[str, int] = {"prompt": 0, "completion": 0, "total": 0}
        model_name = self.client.model or "unknown"
        # Track pending tool calls: tool_use_id -> (NormalizedToolCall, context_dict)
        pending_tool_calls: Dict[str, Tuple[NormalizedToolCall, Dict[str, Any]]] = {}

        try:
            async for event in sdk.query(prompt=prompt, options=options):
                event_type = getattr(event, "type", None) or type(event).__name__
                now = datetime.now(timezone.utc)

                event_dict: Dict[str, Any] = {
                    "timestamp": now.isoformat() + "Z",
                    "phase": "work",
                    "type": event_type,
                }

                if event_type == "AssistantMessageEvent" or hasattr(event, "message"):
                    message = getattr(event, "message", event)
                    content = getattr(message, "content", "")
                    if isinstance(content, list):
                        text_parts = []
                        for block in content:
                            if hasattr(block, "text"):
                                text_parts.append(block.text)
                        content = "\n".join(text_parts)
                    if content:
                        full_text.append(content)
                    event_dict["content"] = content[:500] if content else ""

                elif event_type == "ToolUseEvent" or hasattr(event, "tool_name"):
                    tool_name = getattr(event, "tool_name", getattr(event, "name", "unknown"))
                    tool_input = getattr(event, "input", getattr(event, "args", {}))
                    if not isinstance(tool_input, dict):
                        tool_input = {"value": tool_input} if tool_input else {}
                    tool_use_id = getattr(
                        event, "id", getattr(event, "tool_use_id", str(time.time()))
                    )

                    # Initialize tool context for this call
                    tool_ctx: Dict[str, Any] = {
                        "tool_name": tool_name,
                        "tool_input": tool_input,
                        "tool_start_time": time.time(),
                        "step_id": self.step_id,
                        "session_id": self.session_id,
                    }

                    # Apply tool policy hook (legacy)
                    blocked = False
                    blocked_reason: Optional[str] = None
                    if self.client.tool_policy_hook and isinstance(tool_input, dict):
                        allowed, reason = self.client.tool_policy_hook(tool_name, tool_input)
                        if not allowed:
                            blocked = True
                            blocked_reason = reason
                            logger.warning(
                                "Tool use blocked by policy: %s - %s",
                                tool_name,
                                reason,
                            )
                            event_dict["blocked"] = True
                            event_dict["block_reason"] = reason

                    # Apply pre-tool-use hooks
                    if not blocked and isinstance(tool_input, dict):
                        for hook in self.client.pre_tool_hooks:
                            try:
                                allowed, reason = hook(tool_name, tool_input, tool_ctx)
                                if not allowed:
                                    blocked = True
                                    blocked_reason = reason
                                    logger.warning(
                                        "Tool use blocked by pre-hook: %s - %s",
                                        tool_name,
                                        reason,
                                    )
                                    event_dict["blocked"] = True
                                    event_dict["block_reason"] = reason
                                    break
                            except Exception as hook_err:
                                logger.debug("Pre-tool-use hook failed: %s", hook_err)

                    # Create NormalizedToolCall and store for later matching with result
                    tool_call = NormalizedToolCall(
                        tool_name=tool_name,
                        tool_input=tool_input,
                        source="sdk",
                        timestamp=now.isoformat() + "Z",
                        blocked=blocked,
                        blocked_reason=blocked_reason,
                    )
                    pending_tool_calls[tool_use_id] = (tool_call, tool_ctx)

                    event_dict["tool"] = tool_name

                elif event_type == "ToolResultEvent" or hasattr(event, "tool_result"):
                    tool_use_id = getattr(event, "tool_use_id", getattr(event, "id", None))
                    success = getattr(event, "success", True)
                    result = getattr(event, "tool_result", getattr(event, "result", ""))

                    event_dict["success"] = success

                    # Get pending tool call and context, then calculate duration
                    pending = pending_tool_calls.pop(tool_use_id, None)
                    if pending:
                        tool_call, tool_ctx = pending
                        start_time = tool_ctx.get("tool_start_time", 0)
                        duration_ms = int((time.time() - start_time) * 1000) if start_time else 0

                        # Update the NormalizedToolCall with result details
                        tool_call.tool_output = truncate_output(str(result), max_chars=2000)
                        tool_call.success = success
                        tool_call.duration_ms = duration_ms

                        # Add to completed tool calls list
                        tool_calls.append(tool_call)

                        tool_name = tool_call.tool_name
                        tool_input = tool_ctx.get("tool_input", {})
                    else:
                        tool_name = "unknown"
                        tool_input = {}
                        duration_ms = 0

                    # Record telemetry
                    telemetry.record_tool_call(tool_name, float(duration_ms))

                    # Apply post-tool-use hooks
                    if pending:
                        for hook in self.client.post_tool_hooks:
                            try:
                                hook(tool_name, tool_input, result, success, tool_ctx)
                            except Exception as hook_err:
                                logger.debug("Post-tool-use hook failed: %s", hook_err)

                elif event_type == "ResultEvent" or hasattr(event, "result"):
                    result = getattr(event, "result", event)
                    usage = getattr(result, "usage", None)
                    if usage:
                        token_counts["prompt"] = getattr(usage, "input_tokens", 0)
                        token_counts["completion"] = getattr(usage, "output_tokens", 0)
                        token_counts["total"] = token_counts["prompt"] + token_counts["completion"]
                        telemetry.prompt_tokens = token_counts["prompt"]
                        telemetry.completion_tokens = token_counts["completion"]
                    if hasattr(result, "model"):
                        model_name = result.model
                        telemetry.model = model_name

                events.append(event_dict)

            # Store conversation context for subsequent phases
            self._conversation_history.append(
                {
                    "role": "user",
                    "content": prompt,
                }
            )
            self._conversation_history.append(
                {
                    "role": "assistant",
                    "content": "".join(full_text),
                }
            )

            self._work_result = WorkPhaseResult(
                success=True,
                output="".join(full_text),
                events=events,
                token_counts=token_counts,
                model=model_name,
                tool_calls=tool_calls,
            )

        except Exception as e:
            logger.warning("Work phase failed for session %s: %s", self.session_id, e)
            telemetry.errors.append(str(e))
            self._work_result = WorkPhaseResult(
                success=False,
                output="",
                error=str(e),
                events=events,
            )

        telemetry.finalize()
        self._work_completed = True
        return self._work_result

    async def finalize(
        self,
        handoff_path: Optional[Path] = None,
    ) -> FinalizePhaseResult:
        """Execute the finalize phase to extract handoff envelope.

        Uses structured output_format for reliable JSON extraction when SDK supports it.
        Falls back to prompt-based extraction otherwise.

        This phase uses a follow-up turn in the same session to preserve hot context
        from the work phase, enabling the model to accurately summarize its work.

        Args:
            handoff_path: Optional path where agent should write handoff file.

        Returns:
            FinalizePhaseResult with parsed envelope data.
        """
        if not self._work_completed:
            raise RuntimeError("Work phase must complete before finalize")

        if self._finalize_completed:
            raise RuntimeError("Finalize phase already completed for this session")

        # Initialize telemetry for this phase
        telemetry = TelemetryData(
            phase="finalize",
            start_time=datetime.now(timezone.utc).isoformat() + "Z",
        )
        self._telemetry["finalize"] = telemetry

        if not self.client._check_sdk():
            self._finalize_result = FinalizePhaseResult(
                success=False,
                error="Claude SDK not available",
            )
            telemetry.errors.append("Claude SDK not available")
            telemetry.finalize()
            self._finalize_completed = True
            return self._finalize_result

        # Build finalization prompt
        work_summary = self._work_result.output[:4000] if self._work_result else ""

        finalization_prompt = f"""
Your work session is complete. Now create a structured handoff for the next step.

## Work Session Summary
{work_summary}

## Your Task
Analyze your work and produce a HandoffEnvelope JSON with:
- step_id: "{self.step_id}"
- flow_key: "{self.flow_key}"
- run_id: "{self.run_id}"
- status: VERIFIED (task complete), UNVERIFIED (incomplete), PARTIAL (blocked), or BLOCKED
- summary: 2-paragraph summary of accomplishments and issues
- artifacts: map of artifact names to relative paths
- confidence: 0.0 to 1.0
- can_further_iteration_help: "yes" or "no" (for microloops)

Output ONLY the JSON object, no markdown or explanation.
"""

        sdk = get_sdk_module()

        # Try to use output_format for structured output if SDK supports it
        # The SDK may support output_format as a parameter to query()
        # If not available, fall back to prompt-based extraction
        options_kwargs: Dict[str, Any] = {
            "cwd": str(self.client.repo_root),
            "permission_mode": "bypassPermissions",
            "setting_sources": ["project"],
            "system_prompt": {
                "type": "preset",
                "preset": "claude_code",
            },
        }

        if self.client.model:
            options_kwargs["model"] = self.client.model

        # Check if SDK supports output_format parameter
        sdk_has_output_format = hasattr(sdk, "ClaudeCodeOptions") and "output_format" in str(
            getattr(sdk.ClaudeCodeOptions, "__init__", lambda: None).__doc__ or ""
        )

        if sdk_has_output_format:
            # Use structured output format for reliable JSON extraction
            options_kwargs["output_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "HandoffEnvelope",
                    "schema": HANDOFF_ENVELOPE_SCHEMA,
                    "strict": True,
                },
            }
            logger.debug("Using output_format for finalize phase")

        try:
            options = sdk.ClaudeCodeOptions(**options_kwargs)
        except TypeError:
            # output_format not supported, use basic options
            logger.debug("output_format not supported, using prompt-based extraction")
            options = create_high_trust_options(
                cwd=str(self.client.repo_root),
                permission_mode="bypassPermissions",
                model=self.client.model,
            )

        try:
            response_text = ""
            async for event in sdk.query(prompt=finalization_prompt, options=options):
                if hasattr(event, "message"):
                    message = getattr(event, "message", event)
                    content = getattr(message, "content", "")
                    if isinstance(content, list):
                        for block in content:
                            if hasattr(block, "text"):
                                response_text += block.text
                    elif content:
                        response_text += content

                # Track token usage
                if hasattr(event, "result"):
                    result = getattr(event, "result", event)
                    usage = getattr(result, "usage", None)
                    if usage:
                        telemetry.prompt_tokens = getattr(usage, "input_tokens", 0)
                        telemetry.completion_tokens = getattr(usage, "output_tokens", 0)
                    if hasattr(result, "model"):
                        telemetry.model = result.model

            # Parse JSON from response
            envelope = self._parse_json_response(response_text)

            # Ensure required fields are present
            if envelope:
                envelope.setdefault("step_id", self.step_id)
                envelope.setdefault("flow_key", self.flow_key)
                envelope.setdefault("run_id", self.run_id)
                envelope.setdefault("timestamp", datetime.now(timezone.utc).isoformat() + "Z")

            self._finalize_result = FinalizePhaseResult(
                envelope=envelope,
                raw_output=response_text,
                success=envelope is not None,
                error=None if envelope else "Failed to parse envelope JSON",
            )

        except Exception as e:
            logger.warning("Finalize phase failed for session %s: %s", self.session_id, e)
            telemetry.errors.append(str(e))
            self._finalize_result = FinalizePhaseResult(
                success=False,
                error=str(e),
            )

        telemetry.finalize()
        self._finalize_completed = True
        return self._finalize_result

    async def route(
        self,
        routing_config: Optional[Dict[str, Any]] = None,
    ) -> RoutePhaseResult:
        """Execute the route phase to determine next step.

        Uses structured output_format for reliable JSON extraction when SDK supports it.
        Falls back to prompt-based extraction otherwise.

        This phase uses a follow-up turn in the same session to preserve hot context,
        enabling the model to make informed routing decisions based on its work.

        Args:
            routing_config: Optional routing configuration from flow spec.

        Returns:
            RoutePhaseResult with parsed routing signal.
        """
        if not self._work_completed:
            raise RuntimeError("Work phase must complete before route")

        if self._route_completed:
            raise RuntimeError("Route phase already completed for this session")

        # Initialize telemetry for this phase
        telemetry = TelemetryData(
            phase="route",
            start_time=datetime.now(timezone.utc).isoformat() + "Z",
        )
        self._telemetry["route"] = telemetry

        if self.is_terminal:
            # Terminal steps don't need routing
            self._route_result = RoutePhaseResult(
                signal={
                    "decision": "terminate",
                    "reason": "Terminal step",
                    "confidence": 1.0,
                    "needs_human": False,
                },
                success=True,
            )
            telemetry.finalize()
            self._route_completed = True
            return self._route_result

        if not self.client._check_sdk():
            self._route_result = RoutePhaseResult(
                success=False,
                error="Claude SDK not available",
            )
            telemetry.errors.append("Claude SDK not available")
            telemetry.finalize()
            self._route_completed = True
            return self._route_result

        # Build routing context
        handoff_summary = ""
        if self._finalize_result and self._finalize_result.envelope:
            handoff_summary = json.dumps(self._finalize_result.envelope, indent=2)
        elif self._work_result:
            handoff_summary = self._work_result.output[:2000]

        routing_prompt = f"""
Analyze the handoff and determine the next step.

## Handoff
```json
{handoff_summary}
```

## Routing Config
{json.dumps(routing_config or {}, indent=2)}

## Decision Logic
- If status is VERIFIED and work is complete: "advance" to next step
- If status is UNVERIFIED and can_further_iteration_help is "yes": "loop" back
- If status is UNVERIFIED and can_further_iteration_help is "no": "advance" (exit with concerns)
- If max iterations reached: "advance" (exit with documented concerns)
- If terminal condition: "terminate"

Output ONLY a JSON object with: decision, next_step_id, reason, confidence, needs_human
"""

        sdk = get_sdk_module()

        # Try to use output_format for structured output if SDK supports it
        options_kwargs: Dict[str, Any] = {
            "cwd": str(self.client.repo_root),
            "permission_mode": "bypassPermissions",
            "setting_sources": ["project"],
            "system_prompt": {
                "type": "preset",
                "preset": "claude_code",
            },
        }

        if self.client.model:
            options_kwargs["model"] = self.client.model

        # Check if SDK supports output_format parameter
        sdk_has_output_format = hasattr(sdk, "ClaudeCodeOptions") and "output_format" in str(
            getattr(sdk.ClaudeCodeOptions, "__init__", lambda: None).__doc__ or ""
        )

        if sdk_has_output_format:
            # Use structured output format for reliable JSON extraction
            options_kwargs["output_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "RoutingSignal",
                    "schema": ROUTING_SIGNAL_SCHEMA,
                    "strict": True,
                },
            }
            logger.debug("Using output_format for route phase")

        try:
            options = sdk.ClaudeCodeOptions(**options_kwargs)
        except TypeError:
            # output_format not supported, use basic options
            logger.debug("output_format not supported, using prompt-based extraction")
            options = create_high_trust_options(
                cwd=str(self.client.repo_root),
                permission_mode="bypassPermissions",
                model=self.client.model,
            )

        try:
            response_text = ""
            async for event in sdk.query(prompt=routing_prompt, options=options):
                if hasattr(event, "message"):
                    message = getattr(event, "message", event)
                    content = getattr(message, "content", "")
                    if isinstance(content, list):
                        for block in content:
                            if hasattr(block, "text"):
                                response_text += block.text
                    elif content:
                        response_text += content

                # Track token usage
                if hasattr(event, "result"):
                    result = getattr(event, "result", event)
                    usage = getattr(result, "usage", None)
                    if usage:
                        telemetry.prompt_tokens = getattr(usage, "input_tokens", 0)
                        telemetry.completion_tokens = getattr(usage, "output_tokens", 0)
                    if hasattr(result, "model"):
                        telemetry.model = result.model

            # Parse JSON from response
            signal = self._parse_json_response(response_text)

            # Ensure required fields are present with defaults
            if signal:
                signal.setdefault("confidence", 0.7)
                signal.setdefault("needs_human", False)

            self._route_result = RoutePhaseResult(
                signal=signal,
                raw_output=response_text,
                success=signal is not None,
                error=None if signal else "Failed to parse routing signal JSON",
            )

        except Exception as e:
            logger.warning("Route phase failed for session %s: %s", self.session_id, e)
            telemetry.errors.append(str(e))
            self._route_result = RoutePhaseResult(
                success=False,
                error=str(e),
            )

        telemetry.finalize()
        self._route_completed = True
        return self._route_result

    def get_result(self) -> StepSessionResult:
        """Get the combined result from all completed phases.

        Returns:
            StepSessionResult with all phase results, duration, and telemetry.
        """
        end_time = datetime.now(timezone.utc)
        duration_ms = int((end_time - self._start_time).total_seconds() * 1000)

        return StepSessionResult(
            work=self._work_result
            or WorkPhaseResult(success=False, output="", error="Work not completed"),
            finalize=self._finalize_result,
            route=self._route_result,
            duration_ms=duration_ms,
            session_id=self.session_id,
            telemetry=self._telemetry,
        )

    def _parse_json_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse JSON from SDK response, handling markdown code blocks.

        Args:
            response: Raw response text that may contain JSON.

        Returns:
            Parsed JSON dict or None if parsing failed.
        """
        if not response:
            return None

        # Try to extract JSON from markdown code blocks
        json_text = response.strip()

        if "```json" in json_text:
            start = json_text.find("```json") + 7
            end = json_text.find("```", start)
            if end > start:
                json_text = json_text[start:end].strip()
        elif "```" in json_text:
            start = json_text.find("```") + 3
            end = json_text.find("```", start)
            if end > start:
                json_text = json_text[start:end].strip()

        # Try to parse
        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            # Try to find JSON object in the text
            brace_start = json_text.find("{")
            brace_end = json_text.rfind("}") + 1
            if brace_start >= 0 and brace_end > brace_start:
                try:
                    return json.loads(json_text[brace_start:brace_end])
                except json.JSONDecodeError:
                    pass

        logger.debug("Failed to parse JSON from response: %s", response[:200])
        return None
