"""
Adapters that convert source specs into StepIntent objects.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ..types import FlowSpec, FlowStep, StationSpec
from .models import CompileContext, StepIntent, _dedupe_preserve_order

if TYPE_CHECKING:
    from ..compiler_legacy import FlowNode, StepTemplate


def intent_from_flow_step(
    flow: FlowSpec,
    step: FlowStep,
    station: StationSpec,
    flow_key: str,
) -> StepIntent:
    """Adapt a FlowSpec step into a StepIntent."""
    required_inputs = _dedupe_preserve_order(
        list(station.io.required_inputs) + list(step.inputs)
    )
    required_outputs = _dedupe_preserve_order(
        list(station.io.required_outputs) + list(step.outputs)
    )

    verification_overrides: Dict[str, Any] = {}
    commands = step.sdk_overrides.get("verification_commands")
    if commands:
        verification_overrides["verification_commands"] = list(commands)

    return StepIntent(
        flow_id=flow.id,
        flow_key=flow_key,
        flow_version=flow.version,
        step_id=step.id,
        station_id=station.id,
        objective=step.objective,
        scope=step.scope,
        required_inputs=tuple(required_inputs),
        required_outputs=tuple(required_outputs),
        handoff_path_template=station.handoff.path_template,
        required_fields=station.handoff.required_fields,
        sdk_overrides=step.sdk_overrides,
        verification_overrides=verification_overrides,
    )


def intent_from_flow_node(
    node: "FlowNode",
    template: Optional["StepTemplate"],
    station: StationSpec,
    context: CompileContext,
) -> StepIntent:
    """Adapt a FlowGraph node into a StepIntent."""
    from .prompt_parts import render_template

    objective = node.params.get("objective", f"Execute step {node.node_id}")
    params: Dict[str, Any] = {}

    if template:
        merged_params = {**template.parameters, **node.params}
        params = merged_params
        obj_spec = template.objective if isinstance(template.objective, dict) else {}
        base_template = obj_spec.get("template", "")
        if base_template:
            objective = render_template(base_template, merged_params)

    required_inputs = list(station.io.required_inputs)
    required_outputs = list(station.io.required_outputs)

    if template and template.io_overrides:
        io = template.io_overrides
        required_inputs.extend(io.get("required_inputs", []))
        required_outputs.extend(io.get("required_outputs", []))

    if "inputs" in node.overrides:
        required_inputs.extend(node.overrides["inputs"])
    if "outputs" in node.overrides:
        required_outputs.extend(node.overrides["outputs"])

    required_inputs = _dedupe_preserve_order(required_inputs)
    required_outputs = _dedupe_preserve_order(required_outputs)

    artifacts: List[str] = []
    commands: List[str] = []

    if template and template.constraints:
        artifacts.extend(template.constraints.get("required_artifacts", []))
        commands.extend(template.constraints.get("verification_commands", []))

    if "verification" in node.overrides:
        verification = node.overrides["verification"]
        artifacts.extend(verification.get("required_artifacts", []))
        commands.extend(verification.get("verification_commands", []))

    verification_overrides: Dict[str, Any] = {}
    if artifacts:
        verification_overrides["required_artifacts"] = _dedupe_preserve_order(artifacts)
    if commands:
        verification_overrides["verification_commands"] = _dedupe_preserve_order(commands)

    flow_id = context.run_id
    flow_key = context.run_id.split("-")[0] if context.run_id else ""

    return StepIntent(
        flow_id=flow_id,
        flow_key=flow_key,
        flow_version=1,
        step_id=node.node_id,
        station_id=station.id,
        objective=objective,
        scope=node.params.get("scope"),
        required_inputs=tuple(required_inputs),
        required_outputs=tuple(required_outputs),
        handoff_path_template=station.handoff.path_template,
        required_fields=station.handoff.required_fields,
        sdk_overrides=node.overrides,
        verification_overrides=verification_overrides,
        params=params,
        template_id=template.id if template else None,
        template_version=template.version if template else None,
    )
