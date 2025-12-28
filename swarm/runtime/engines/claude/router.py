"""
router.py - Routing logic for Claude step engine.

Handles:
- Microloop termination detection
- Router session execution
- Routing signal generation
- Spec-based deterministic routing
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union

from swarm.runtime.types import RoutingDecision, RoutingSignal
from swarm.spec.types import RoutingConfig, RoutingKind

from ..models import RoutingContext, StepContext

logger = logging.getLogger(__name__)


# Router prompt template for agentic routing decisions
ROUTER_PROMPT_TEMPLATE = """
You are a routing resolver. Your job is to convert natural language handoff text plus step routing configuration into a deterministic RoutingSignal JSON.

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
  can_further_iteration_help: {can_further_iteration_help}
current_iteration: {current_iteration}
```

## Decision Logic

### Linear Flow
- If `loop_target` is reached and `success_values` contains the target value -> **"proceed"**
- If `loop_target` is not reached but `max_iterations` is exhausted -> **"rerun"**
- If `loop_target` is not reached and `can_further_iteration_help` is false -> **"blocked"**

### Microloop Flow
- If `success_values` contains the current status value -> **"proceed"** (exit loop)
- If `max_iterations` is exhausted -> **"proceed"** (exit with documented concerns)
- If `can_further_iteration_help` is false -> **"proceed"** (exit loop, no viable fix path)
- Otherwise if UNVERIFIED and iterations < max -> **"loop"** back to loop_target

### Branching Flow
- If explicit user routing hint exists in handoff text -> **"route"** with the specified step_id

### Default
- If no conditions met -> **"proceed"** with `next_step_id: null`

## Confidence Scoring
- **1.0**: Clear, confident routing decision
- **0.7**: Some ambiguity but reasonable inference
- **0.5**: Ambiguous routing, may need human review
- **0.0**: Clear, unambiguous routing decision (legacy: inverted scale)

## Output Format

Output ONLY a valid JSON object with this structure (no markdown, no explanation):
```json
{{
  "decision": "proceed" | "rerun" | "blocked" | "loop" | "route",
  "next_step_id": "<step_id or null>",
  "route": null,
  "reason": "<explanation for this routing decision>",
  "confidence": <0.0 to 1.0>,
  "needs_human": <true | false>
}}
```

Note: For backward compatibility, "proceed" maps to "advance", and "rerun" maps to "loop".

Analyze the handoff and emit your routing decision now.
"""


def load_resolver_template(repo_root: Optional[Path], resolver_name: str) -> Optional[str]:
    """Load resolver template from swarm/prompts/resolvers/*.md.

    Resolver templates provide customizable prompts for specific routing/decision
    tasks. If a template exists, it is used instead of the hardcoded prompt.

    Args:
        repo_root: Repository root path.
        resolver_name: The resolver name (e.g., "routing_signal").

    Returns:
        The resolver template content, or None if not found.
    """
    if not repo_root:
        return None

    resolver_path = (
        Path(repo_root) / "swarm" / "prompts" / "resolvers" / f"{resolver_name}.md"
    )
    if not resolver_path.exists():
        logger.debug("Resolver template not found: %s", resolver_path)
        return None

    try:
        content = resolver_path.read_text(encoding="utf-8")

        # Strip YAML frontmatter (between --- markers) if present
        if content.startswith("---"):
            end_marker = content.find("---", 3)
            if end_marker != -1:
                body_start = end_marker + 3
                if body_start < len(content) and content[body_start] == "\n":
                    body_start += 1
                content = content[body_start:]

        logger.debug("Loaded resolver template: %s", resolver_path)
        return content.strip()

    except (OSError, IOError) as e:
        logger.warning("Failed to load resolver template %s: %s", resolver_name, e)
        return None


def check_microloop_termination(
    handoff_data: Dict[str, Any],
    routing_config: Dict[str, Any],
    current_iteration: int,
) -> Optional[RoutingSignal]:
    """Check if microloop should terminate based on resolver spec logic.

    This implements the microloop termination logic from routing_signal.md:
    1. Check if loop_target reached with success_values
    2. Check if max_iterations exhausted
    3. Check if can_further_iteration_help is false in handoff

    Args:
        handoff_data: The handoff JSON from JIT finalization.
        routing_config: The step's routing configuration from extra.routing.
        current_iteration: Current loop iteration count.

    Returns:
        RoutingSignal if termination condition met, None to continue looping.
    """
    # Extract routing configuration
    loop_target = routing_config.get("loop_target")
    success_values = routing_config.get("loop_success_values", ["VERIFIED"])
    max_iterations = routing_config.get("max_iterations", 3)
    loop_condition_field = routing_config.get("loop_condition_field", "status")

    # Get the current status from handoff
    current_status = handoff_data.get(loop_condition_field, "").upper()

    # Check can_further_iteration_help from handoff (explicit signal from critic)
    can_further_help = handoff_data.get("can_further_iteration_help", True)
    if isinstance(can_further_help, str):
        can_further_help = can_further_help.lower() in ("yes", "true", "1")

    # Condition 1: Success status reached - exit loop with ADVANCE
    if current_status in [s.upper() for s in success_values]:
        return RoutingSignal(
            decision=RoutingDecision.ADVANCE,
            next_step_id=None,  # Orchestrator determines next step
            reason=f"Loop target reached: {loop_condition_field}={current_status}",
            confidence=1.0,
            needs_human=False,
        )

    # Condition 2: Max iterations exhausted - exit loop with ADVANCE
    if current_iteration >= max_iterations:
        return RoutingSignal(
            decision=RoutingDecision.ADVANCE,
            next_step_id=None,
            reason=f"Max iterations reached ({current_iteration}/{max_iterations}), exiting with documented concerns",
            confidence=0.7,
            needs_human=True,  # Human should review incomplete work
        )

    # Condition 3: can_further_iteration_help is false - exit loop
    if not can_further_help:
        return RoutingSignal(
            decision=RoutingDecision.ADVANCE,
            next_step_id=None,
            reason="Critic indicated no further iteration can help, exiting loop",
            confidence=0.8,
            needs_human=True,  # Human should review why iteration was not helpful
        )

    # No termination condition met - return None to continue looping
    return None


async def run_router_session(
    handoff_data: Dict[str, Any],
    ctx: StepContext,
    cwd: str,
) -> Optional[RoutingSignal]:
    """Run a lightweight router session to decide the next step.

    This is a fresh, short-lived session that analyzes the handoff
    and produces a routing decision. Uses resolver template if available,
    otherwise falls back to ROUTER_PROMPT_TEMPLATE.

    Uses the unified claude_sdk adapter for SDK access.

    Args:
        handoff_data: The handoff JSON from JIT finalization.
        ctx: Step execution context with routing configuration.
        cwd: Working directory for the session.

    Returns:
        RoutingSignal if routing was determined, None if routing failed.
    """
    from swarm.runtime.claude_sdk import get_sdk_module, create_high_trust_options

    sdk = get_sdk_module()
    query = sdk.query

    # Extract routing config from context
    routing = ctx.routing or RoutingContext()
    routing_config = ctx.extra.get("routing", {})
    current_iteration = routing.loop_iteration
    routing_kind = routing_config.get("kind", "linear")

    # For microloops, check termination conditions before LLM call
    if routing_kind == "microloop":
        termination_signal = check_microloop_termination(
            handoff_data=handoff_data,
            routing_config=routing_config,
            current_iteration=current_iteration,
        )
        if termination_signal:
            logger.debug(
                "Microloop termination detected for step %s: %s",
                ctx.step_id,
                termination_signal.reason,
            )
            return termination_signal

    # Try to load resolver template, fall back to hardcoded template
    resolver_template = load_resolver_template(ctx.repo_root, "routing_signal")

    # Prepare template variables
    template_vars = {
        "handoff_json": json.dumps(handoff_data, indent=2),
        "step_id": ctx.step_id,
        "flow_key": ctx.flow_key,
        "routing_kind": routing_kind,
        "routing_next": routing_config.get("next", "null"),
        "loop_target": routing_config.get("loop_target", "null"),
        "loop_condition_field": routing_config.get("loop_condition_field", "status"),
        "loop_success_values": routing_config.get("loop_success_values", ["VERIFIED"]),
        "max_iterations": routing_config.get("max_iterations", 3),
        "can_further_iteration_help": handoff_data.get("can_further_iteration_help", True),
        "current_iteration": current_iteration,
    }

    # Build router prompt from resolver template or fallback
    if resolver_template:
        router_prompt = f"""
## Handoff from Previous Step

```json
{template_vars['handoff_json']}
```

## Step Routing Configuration

```yaml
step_id: {template_vars['step_id']}
flow_key: {template_vars['flow_key']}
routing:
  kind: {template_vars['routing_kind']}
  next: {template_vars['routing_next']}
  loop_target: {template_vars['loop_target']}
  loop_condition_field: {template_vars['loop_condition_field']}
  loop_success_values: {template_vars['loop_success_values']}
  max_iterations: {template_vars['max_iterations']}
  can_further_iteration_help: {template_vars['can_further_iteration_help']}
current_iteration: {template_vars['current_iteration']}
```

{resolver_template}
"""
        logger.debug("Using resolver template for routing")
    else:
        router_prompt = ROUTER_PROMPT_TEMPLATE.format(**template_vars)
        logger.debug("Using fallback ROUTER_PROMPT_TEMPLATE for routing")

    # Router uses minimal options via adapter
    options = create_high_trust_options(
        cwd=cwd,
        permission_mode="bypassPermissions",
    )

    # Collect router response
    router_response = ""

    try:
        logger.debug("Starting router session for step %s", ctx.step_id)

        async for event in query(
            prompt=router_prompt,
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
            "proceed": RoutingDecision.ADVANCE,
            "rerun": RoutingDecision.LOOP,
            "blocked": RoutingDecision.TERMINATE,
            "route": RoutingDecision.BRANCH,
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


def route_step_stub(
    ctx: StepContext,
    handoff_data: Dict[str, Any],
) -> Optional[RoutingSignal]:
    """Stub implementation of route_step for testing.

    Uses deterministic routing based on routing config from ctx.extra.
    This allows testing of the orchestrator's routing logic without LLM calls.

    Args:
        ctx: Step execution context.
        handoff_data: Parsed handoff data.

    Returns:
        RoutingSignal with deterministic routing decision.
    """
    routing_config = ctx.extra.get("routing", {})

    # Check for microloop termination
    if routing_config.get("kind") == "microloop":
        status = handoff_data.get("status", "").upper()
        success_values = routing_config.get("loop_success_values", ["VERIFIED"])

        if status in [v.upper() for v in success_values]:
            next_step = routing_config.get("next")
            return RoutingSignal(
                decision=RoutingDecision.ADVANCE,
                next_step_id=next_step,
                reason=f"stub_microloop_exit:{status}",
                confidence=1.0,
                needs_human=False,
            )

        # Check can_further_iteration_help
        can_help = handoff_data.get("can_further_iteration_help", "no")
        if isinstance(can_help, str) and can_help.lower() == "no":
            next_step = routing_config.get("next")
            return RoutingSignal(
                decision=RoutingDecision.ADVANCE,
                next_step_id=next_step,
                reason="stub_microloop_no_further_help",
                confidence=1.0,
                needs_human=False,
            )

    # Default: advance to next step
    next_step = routing_config.get("next")
    if next_step:
        return RoutingSignal(
            decision=RoutingDecision.ADVANCE,
            next_step_id=next_step,
            reason="stub_linear_advance",
            confidence=1.0,
            needs_human=False,
        )

    # No next step - terminate flow
    return RoutingSignal(
        decision=RoutingDecision.TERMINATE,
        reason="stub_flow_complete",
        confidence=1.0,
        needs_human=False,
    )


def route_from_routing_config(
    routing_config: RoutingConfig,
    handoff_status: str,
    iteration_count: int = 0,
) -> Optional[RoutingSignal]:
    """Interpret RoutingConfig from specs to produce RoutingSignal.

    This function provides deterministic routing based on the spec-first
    architecture. It enables routing decisions without requiring an LLM call
    for cases where the routing logic is fully specified in the flow spec.

    Args:
        routing_config: The RoutingConfig from the step's FlowStep.routing.
        handoff_status: The status value from the handoff (e.g., "VERIFIED", "UNVERIFIED").
        iteration_count: Current iteration count for microloop tracking (0-based).

    Returns:
        RoutingSignal if routing can be determined deterministically,
        None if routing requires LLM decision (e.g., ambiguous branch conditions).

    Examples:
        >>> config = RoutingConfig(kind=RoutingKind.TERMINAL)
        >>> signal = route_from_routing_config(config, "VERIFIED")
        >>> signal.decision
        <RoutingDecision.TERMINATE: 'terminate'>

        >>> config = RoutingConfig(kind=RoutingKind.LINEAR, next="step_2")
        >>> signal = route_from_routing_config(config, "succeeded")
        >>> signal.next_step_id
        'step_2'
    """
    # Normalize handoff status for comparison (handle case variations)
    normalized_status = handoff_status.upper() if handoff_status else ""

    # Handle terminal routing - always terminates
    if routing_config.kind == RoutingKind.TERMINAL:
        return RoutingSignal(
            decision=RoutingDecision.TERMINATE,
            reason="spec_terminal",
            confidence=1.0,
            needs_human=False,
        )

    # Handle linear routing - advances to next step or terminates
    if routing_config.kind == RoutingKind.LINEAR:
        if routing_config.next:
            return RoutingSignal(
                decision=RoutingDecision.ADVANCE,
                next_step_id=routing_config.next,
                reason="spec_linear",
                confidence=1.0,
                needs_human=False,
            )
        # Linear with no next step means flow complete
        return RoutingSignal(
            decision=RoutingDecision.TERMINATE,
            reason="spec_linear_no_next",
            confidence=1.0,
            needs_human=False,
        )

    # Handle microloop routing - checks success, max iterations, or loops back
    if routing_config.kind == RoutingKind.MICROLOOP:
        # Normalize success values for comparison
        success_values_upper = tuple(
            v.upper() for v in routing_config.loop_success_values
        )

        # Check if success condition met
        if normalized_status in success_values_upper:
            return RoutingSignal(
                decision=RoutingDecision.ADVANCE,
                next_step_id=routing_config.next,
                reason="spec_microloop_verified",
                confidence=1.0,
                needs_human=False,
            )

        # Check if max iterations reached
        if iteration_count >= routing_config.max_iterations:
            return RoutingSignal(
                decision=RoutingDecision.ADVANCE,
                next_step_id=routing_config.next,
                reason="spec_microloop_max_iterations",
                confidence=0.7,
                needs_human=True,  # Human should review incomplete work
            )

        # Loop back to target
        return RoutingSignal(
            decision=RoutingDecision.LOOP,
            next_step_id=routing_config.loop_target,
            reason="spec_microloop_continue",
            confidence=1.0,
            needs_human=False,
        )

    # Handle branch routing - routes based on status matching branches
    if routing_config.kind == RoutingKind.BRANCH:
        # Check if status matches any branch
        if routing_config.branches:
            # Try exact match first
            if handoff_status in routing_config.branches:
                return RoutingSignal(
                    decision=RoutingDecision.BRANCH,
                    next_step_id=routing_config.branches[handoff_status],
                    route=handoff_status,
                    reason="spec_branch",
                    confidence=1.0,
                    needs_human=False,
                )
            # Try case-insensitive match
            for branch_key, branch_target in routing_config.branches.items():
                if branch_key.upper() == normalized_status:
                    return RoutingSignal(
                        decision=RoutingDecision.BRANCH,
                        next_step_id=branch_target,
                        route=branch_key,
                        reason="spec_branch",
                        confidence=1.0,
                        needs_human=False,
                    )

        # Fallback to next if no matching branch
        if routing_config.next:
            return RoutingSignal(
                decision=RoutingDecision.ADVANCE,
                next_step_id=routing_config.next,
                reason="spec_branch_default",
                confidence=0.8,
                needs_human=False,
            )

    # Routing cannot be determined deterministically - requires LLM decision
    return None
