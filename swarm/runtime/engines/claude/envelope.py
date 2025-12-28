"""
envelope.py - HandoffEnvelope creation and writing for Claude step engine.

Handles:
- Envelope creation from step results
- Envelope writing to disk
- Fallback envelope generation
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Try to import jsonschema, graceful fallback if not available
try:
    import jsonschema

    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False
    jsonschema = None  # type: ignore[assignment]

from swarm.runtime.path_helpers import (
    ensure_handoff_dir,
    handoff_envelope_path as make_handoff_envelope_path,
)
from swarm.runtime.types import (
    HandoffEnvelope,
    RoutingDecision,
    RoutingSignal,
    handoff_envelope_to_dict,
)

from ..models import StepContext, StepResult

logger = logging.getLogger(__name__)

# Cached schema to avoid repeated file reads
_HANDOFF_SCHEMA: Optional[Dict[str, Any]] = None
_ROUTING_SIGNAL_SCHEMA: Optional[Dict[str, Any]] = None


def _load_handoff_schema() -> Optional[Dict[str, Any]]:
    """Load handoff envelope schema, caching result.

    Searches for the schema in multiple locations relative to
    the file location and repo root.

    Returns:
        The parsed JSON schema as a dictionary, or None if not found.
    """
    global _HANDOFF_SCHEMA
    if _HANDOFF_SCHEMA is not None:
        return _HANDOFF_SCHEMA

    # Find schema relative to this file or repo root
    schema_paths = [
        Path(__file__).parent.parent.parent.parent / "schemas" / "handoff_envelope.schema.json",
        Path("swarm/schemas/handoff_envelope.schema.json"),
    ]

    for path in schema_paths:
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    _HANDOFF_SCHEMA = json.load(f)
                return _HANDOFF_SCHEMA
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to load handoff schema from %s: %s", path, e)
                continue

    return None


def _load_routing_signal_schema() -> Optional[Dict[str, Any]]:
    """Load routing signal schema, caching result.

    Returns:
        The parsed JSON schema as a dictionary, or None if not found.
    """
    global _ROUTING_SIGNAL_SCHEMA
    if _ROUTING_SIGNAL_SCHEMA is not None:
        return _ROUTING_SIGNAL_SCHEMA

    schema_paths = [
        Path(__file__).parent.parent.parent.parent / "schemas" / "routing_signal.schema.json",
        Path("swarm/schemas/routing_signal.schema.json"),
    ]

    for path in schema_paths:
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    _ROUTING_SIGNAL_SCHEMA = json.load(f)
                return _ROUTING_SIGNAL_SCHEMA
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to load routing signal schema from %s: %s", path, e)
                continue

    return None


def _create_schema_resolver() -> Optional[Any]:
    """Create a JSON schema resolver that handles $ref to routing_signal.schema.json.

    Returns:
        A jsonschema RefResolver, or None if schemas not available.
    """
    if not JSONSCHEMA_AVAILABLE:
        return None

    handoff_schema = _load_handoff_schema()
    routing_schema = _load_routing_signal_schema()

    if handoff_schema is None:
        return None

    # Create a store with the routing signal schema
    store: Dict[str, Any] = {}
    if routing_schema is not None:
        store["https://swarm.dev/schemas/routing_signal.schema.json"] = routing_schema

    # Create resolver with the store
    resolver = jsonschema.RefResolver.from_schema(handoff_schema, store=store)
    return resolver


def validate_handoff_envelope(envelope_dict: Dict[str, Any]) -> List[str]:
    """Validate envelope dict against JSON schema.

    Performs validation of the HandoffEnvelope dictionary against
    the handoff_envelope.schema.json schema. Gracefully handles
    missing dependencies or schema files.

    Args:
        envelope_dict: The envelope dictionary to validate.

    Returns:
        List of validation error messages (empty if valid or
        validation could not be performed).
    """
    if not JSONSCHEMA_AVAILABLE:
        logger.debug("jsonschema not available, skipping envelope validation")
        return []

    schema = _load_handoff_schema()
    if schema is None:
        logger.debug("Handoff envelope schema not found, skipping validation")
        return []

    errors: List[str] = []
    try:
        # Create resolver to handle $ref to routing_signal schema
        resolver = _create_schema_resolver()
        if resolver is not None:
            jsonschema.validate(envelope_dict, schema, resolver=resolver)
        else:
            jsonschema.validate(envelope_dict, schema)
    except jsonschema.ValidationError as e:
        json_path = e.json_path if hasattr(e, "json_path") else str(list(e.absolute_path))
        errors.append(f"Validation error at {json_path}: {e.message}")
    except jsonschema.SchemaError as e:
        errors.append(f"Schema error: {e.message}")
    except Exception as e:
        # Catch any other unexpected errors during validation
        errors.append(f"Unexpected validation error: {str(e)}")

    return errors


def _is_strict_validation_enabled() -> bool:
    """Check if strict envelope validation mode is enabled.

    Returns:
        True if SWARM_STRICT_ENVELOPE_VALIDATION is set to a truthy value.
    """
    strict_env = os.environ.get("SWARM_STRICT_ENVELOPE_VALIDATION", "").lower()
    return strict_env in ("1", "true", "yes", "on")


def create_fallback_envelope(
    ctx: StepContext,
    step_result: StepResult,
    routing_signal: Optional[RoutingSignal],
    work_summary: str,
    file_changes: Optional[Dict[str, Any]] = None,
) -> HandoffEnvelope:
    """Create a fallback HandoffEnvelope without LLM assistance.

    Used when envelope_writer.md template is not available or parsing fails.

    Args:
        ctx: Step execution context.
        step_result: Result from step execution.
        routing_signal: Routing decision from router session (may be None).
        work_summary: Summary text from the step's work session.
        file_changes: Forensic file mutation scan results (optional).

    Returns:
        HandoffEnvelope with basic step information.
    """
    envelope = HandoffEnvelope(
        step_id=ctx.step_id,
        flow_key=ctx.flow_key,
        run_id=ctx.run_id,
        routing_signal=routing_signal
        or RoutingSignal(
            decision=RoutingDecision.ADVANCE,
            reason="default_advance",
            confidence=0.7,
        ),
        summary=work_summary[:2000]
        if work_summary
        else f"Step {ctx.step_id} completed with status {step_result.status}",
        artifacts=step_result.artifacts or {},
        file_changes=file_changes or {},
        status=step_result.status,
        error=step_result.error,
        duration_ms=step_result.duration_ms,
    )

    # Write envelope to disk
    envelope_path = write_envelope_to_disk(ctx, envelope)
    if envelope_path:
        logger.debug("Wrote fallback handoff envelope to %s", envelope_path)

    return envelope


class EnvelopeValidationError(Exception):
    """Raised when envelope validation fails in strict mode."""

    def __init__(self, errors: List[str]) -> None:
        self.errors = errors
        super().__init__(f"Envelope validation failed: {'; '.join(errors)}")


def write_envelope_to_disk(
    ctx: StepContext,
    envelope: HandoffEnvelope,
) -> Optional[Path]:
    """Write HandoffEnvelope to disk at RUN_BASE/<flow_key>/handoff/<step_id>.json.

    Validates the envelope against the JSON schema before writing. In normal
    mode, validation errors are logged as warnings but writing proceeds.
    When SWARM_STRICT_ENVELOPE_VALIDATION is set, validation errors raise
    an EnvelopeValidationError.

    Args:
        ctx: Step execution context.
        envelope: The HandoffEnvelope to write.

    Returns:
        Path to the written file, or None if writing failed.

    Raises:
        EnvelopeValidationError: If validation fails and strict mode is enabled.
    """
    try:
        # Ensure handoff directory exists
        ensure_handoff_dir(ctx.run_base)

        # Generate envelope file path
        envelope_path = make_handoff_envelope_path(ctx.run_base, ctx.step_id)

        # Convert envelope to dict for JSON serialization
        envelope_dict = handoff_envelope_to_dict(envelope)

        # Validate envelope before writing
        validation_errors = validate_handoff_envelope(envelope_dict)
        if validation_errors:
            if _is_strict_validation_enabled():
                logger.error(
                    "Envelope validation failed for step %s: %s",
                    ctx.step_id,
                    validation_errors,
                )
                raise EnvelopeValidationError(validation_errors)
            else:
                logger.warning(
                    "Envelope validation warnings for step %s: %s",
                    ctx.step_id,
                    validation_errors,
                )

        # Write to disk
        with envelope_path.open("w", encoding="utf-8") as f:
            json.dump(envelope_dict, f, indent=2)

        return envelope_path

    except EnvelopeValidationError:
        # Re-raise validation errors in strict mode
        raise
    except (OSError, IOError) as e:
        logger.warning(
            "Failed to write handoff envelope for step %s: %s", ctx.step_id, e
        )
        return None


async def write_handoff_envelope(
    ctx: StepContext,
    step_result: StepResult,
    routing_signal: Optional[RoutingSignal],
    work_summary: str,
    file_changes: Optional[Dict[str, Any]] = None,
) -> Optional[HandoffEnvelope]:
    """Write structured HandoffEnvelope using envelope_writer resolver.

    Called after JIT finalization to create the durable handoff artifact.
    Uses the envelope_writer.md template to generate a structured envelope
    with routing signal, summary, and artifact pointers.

    Args:
        ctx: Step execution context with flow/step metadata.
        step_result: Result from step execution.
        routing_signal: Routing decision from router session (may be None).
        work_summary: Summary text from the step's work session.
        file_changes: Forensic file mutation scan results (optional).

    Returns:
        HandoffEnvelope if successfully created, None otherwise.
    """
    # Load envelope_writer.md template
    template_path = (
        Path(ctx.repo_root) / "swarm" / "prompts" / "resolvers" / "envelope_writer.md"
        if ctx.repo_root
        else Path("swarm/prompts/resolvers/envelope_writer.md")
    )

    if not template_path.exists():
        logger.warning("envelope_writer.md template not found at %s", template_path)
        return create_fallback_envelope(
            ctx, step_result, routing_signal, work_summary, file_changes
        )

    try:
        template_content = template_path.read_text(encoding="utf-8")
    except (OSError, IOError) as e:
        logger.warning("Failed to load envelope_writer.md: %s", e)
        return create_fallback_envelope(
            ctx, step_result, routing_signal, work_summary, file_changes
        )

    # Import SDK here to avoid circular imports
    from swarm.runtime.claude_sdk import get_sdk_module, create_high_trust_options

    sdk = get_sdk_module()
    query = sdk.query

    # Build input data for the envelope writer
    routing_data = {
        "decision": routing_signal.decision.value if routing_signal else "advance",
        "next_step_id": routing_signal.next_step_id if routing_signal else None,
        "route": routing_signal.route if routing_signal else None,
        "reason": routing_signal.reason if routing_signal else "default_advance",
        "confidence": routing_signal.confidence if routing_signal else 0.7,
        "needs_human": routing_signal.needs_human if routing_signal else False,
    }

    # Collect artifact information
    artifacts_created = step_result.artifacts or {}

    # Build the prompt for envelope writer
    envelope_input = f"""
## Step Execution Results

Step ID: {ctx.step_id}
Flow key: {ctx.flow_key}
Run ID: {ctx.run_id}
Status: {step_result.status}
Duration: {step_result.duration_ms} ms
Error: {step_result.error or "None"}

## Work Summary
{work_summary[:4000] if work_summary else "No summary available."}

## Artifacts Created/Modified
{json.dumps(artifacts_created, indent=2)}

## Routing Signal
{json.dumps(routing_data, indent=2)}

---
{template_content}
"""

    # Set up working directory
    cwd = str(ctx.repo_root) if ctx.repo_root else str(Path.cwd())

    # Envelope writer uses minimal options
    options = create_high_trust_options(
        cwd=cwd,
        permission_mode="bypassPermissions",
    )

    # Collect envelope writer response
    envelope_response = ""

    try:
        logger.debug("Starting envelope writer session for step %s", ctx.step_id)

        async for event in query(
            prompt=envelope_input,
            options=options,
        ):
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
                    envelope_response += content

        logger.debug("Envelope writer session complete for step %s", ctx.step_id)

        # Parse JSON from response
        json_match = None
        if "```json" in envelope_response:
            start = envelope_response.find("```json") + 7
            end = envelope_response.find("```", start)
            if end > start:
                json_match = envelope_response[start:end].strip()
        elif "```" in envelope_response:
            start = envelope_response.find("```") + 3
            end = envelope_response.find("```", start)
            if end > start:
                json_match = envelope_response[start:end].strip()
        else:
            json_match = envelope_response.strip()

        if not json_match:
            logger.warning("Envelope writer response contained no parseable JSON")
            return create_fallback_envelope(
                ctx, step_result, routing_signal, work_summary, file_changes
            )

        envelope_data = json.loads(json_match)

        # Create HandoffEnvelope from parsed data
        envelope = HandoffEnvelope(
            step_id=envelope_data.get("step_id", ctx.step_id),
            flow_key=envelope_data.get("flow_key", ctx.flow_key),
            run_id=envelope_data.get("run_id", ctx.run_id),
            routing_signal=routing_signal
            or RoutingSignal(
                decision=RoutingDecision.ADVANCE,
                reason="default_advance",
                confidence=0.7,
            ),
            summary=envelope_data.get(
                "summary", work_summary[:2000] if work_summary else ""
            ),
            artifacts=envelope_data.get("artifacts", {}),
            file_changes=file_changes or {},
            status=envelope_data.get("status", step_result.status),
            error=envelope_data.get("error"),
            duration_ms=envelope_data.get("duration_ms", step_result.duration_ms),
        )

        # Write envelope to disk
        envelope_path = write_envelope_to_disk(ctx, envelope)
        if envelope_path:
            logger.debug("Wrote handoff envelope to %s", envelope_path)

        return envelope

    except json.JSONDecodeError as e:
        logger.warning(
            "Failed to parse envelope writer response as JSON: %s", e
        )
        return create_fallback_envelope(
            ctx, step_result, routing_signal, work_summary, file_changes
        )
    except Exception as e:
        logger.warning(
            "Envelope writer session failed for step %s: %s", ctx.step_id, e
        )
        return create_fallback_envelope(
            ctx, step_result, routing_signal, work_summary, file_changes
        )
