# swarm/tools/validation/validators/flows/invariants.py
"""Flow invariant validation functions.

Validates structural invariants that all flows must satisfy:
- No empty flows (each flow must have at least one step)
- No agentless steps (each step must have agents or be marked human_only)
"""

from typing import Any, Dict

from swarm.validator import ValidationResult
from swarm.tools.validation.helpers import FLOWS_CONFIG_DIR


def validate_no_empty_flows(flow_configs: Dict[str, Dict[str, Any]]) -> ValidationResult:
    """
    Validate that each flow has at least one step.

    Invariant 1: No empty flows
    """
    result = ValidationResult()

    for flow_id, config in flow_configs.items():
        if not config.get("steps"):
            flow_file = FLOWS_CONFIG_DIR / f"{flow_id}.yaml"
            location = f"swarm/config/flows/{flow_id}.yaml"

            result.add_error(
                "FLOW",
                location,
                f"Flow '{flow_id}' has no steps",
                f"Add at least one step to {location}, or remove the flow definition",
                file_path=str(flow_file)
            )

    return result


def validate_no_agentless_steps(flow_configs: Dict[str, Dict[str, Any]]) -> ValidationResult:
    """
    Validate that each step has agents or is marked human_only.

    Invariant 2: No agentless steps (unless explicitly marked as human_only)
    """
    result = ValidationResult()

    for flow_id, config in flow_configs.items():
        for step in config.get("steps", []):
            if not step.get("agents") and not step.get("human_only"):
                flow_file = FLOWS_CONFIG_DIR / f"{flow_id}.yaml"
                location = f"swarm/config/flows/{flow_id}.yaml"

                result.add_error(
                    "FLOW",
                    location,
                    f"Step '{flow_id}/{step['id']}' has no agents and is not marked 'kind: human_only'",
                    "Either add agents to the step or mark it with 'kind: human_only'",
                    file_path=str(flow_file),
                    line_number=step.get("line")
                )

    return result
