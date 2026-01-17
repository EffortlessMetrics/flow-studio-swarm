# swarm/tools/validation/validators/flows/utility_graphs.py
"""Utility flow graph validation.

Validates utility flow graph specifications to ensure consistency:
- Utility flows (is_utility_flow=true) must have injection_trigger
- Utility flows should use 'return' or 'pause' for next_flow
- Utility flows should have flow_number >= 8
- Main SDLC flows (1-7) should not be marked as utility flows
"""

import json
import re

from swarm.validator import ValidationResult
from swarm.tools.validation.helpers import ROOT


def validate_utility_flow_graphs() -> ValidationResult:
    """
    Validate utility flow graph specifications.

    FR-UTILITY: Utility Flow Consistency
    Checks:
    - If is_utility_flow is true, injection_trigger should be defined
    - If is_utility_flow is true, on_complete.next_flow should be "return" or "pause"
    - If is_utility_flow is true, flow_number should be >= 8
    - Utility flows should not have next_flow pointing to a flow spec ID
    - Main SDLC flows (1-7) should not have is_utility_flow=true
    """
    result = ValidationResult()

    flow_graphs_dir = ROOT / "swarm" / "spec" / "flows"

    if not flow_graphs_dir.is_dir():
        return result

    # Valid utility flow next_flow values
    valid_utility_next_flows = {"return", "pause"}

    for graph_file in sorted(flow_graphs_dir.glob("*.graph.json")):
        if graph_file.is_symlink():
            continue

        rel_path = graph_file.relative_to(ROOT)

        try:
            content = graph_file.read_text(encoding="utf-8")
            graph_data = json.loads(content)
        except json.JSONDecodeError as e:
            result.add_error(
                "UTILITY",
                str(rel_path),
                f"Invalid JSON in flow graph: {e}",
                "Fix JSON syntax errors in the flow graph file",
                file_path=str(graph_file)
            )
            continue
        except Exception as e:
            result.add_error(
                "UTILITY",
                str(rel_path),
                f"Failed to read flow graph: {e}",
                "Check file permissions and encoding",
                file_path=str(graph_file)
            )
            continue

        # Extract relevant fields
        flow_number = graph_data.get("flow_number", 0)
        metadata = graph_data.get("metadata", {})
        is_utility_flow = metadata.get("is_utility_flow", False)
        injection_trigger = metadata.get("injection_trigger")
        on_complete = graph_data.get("on_complete", {})
        next_flow = on_complete.get("next_flow", "")
        flow_id = graph_data.get("id", graph_file.stem)

        # Validation Rule 1: Utility flows need injection_trigger
        if is_utility_flow and not injection_trigger:
            result.add_error(
                "UTILITY",
                str(rel_path),
                f"Utility flow '{flow_id}' is missing injection_trigger in metadata",
                "Add 'injection_trigger' to metadata section (e.g., 'upstream_diverged', 'lint_failure')",
                file_path=str(graph_file)
            )

        # Validation Rule 2: Utility flows should use 'return' or 'pause' for next_flow
        if is_utility_flow:
            if next_flow and next_flow not in valid_utility_next_flows:
                # Check if it looks like a flow spec ID (e.g., "4-gate")
                if re.match(r"^\d+-[a-z]+$", next_flow):
                    result.add_error(
                        "UTILITY",
                        str(rel_path),
                        f"Utility flow '{flow_id}' has on_complete.next_flow='{next_flow}' which is a flow spec ID; utility flows should use 'return' or 'pause'",
                        "Change on_complete.next_flow to 'return' (to resume interrupted flow) or 'pause' (for human intervention)",
                        file_path=str(graph_file)
                    )
                else:
                    # Warn about unknown next_flow value
                    result.add_warning(
                        "UTILITY",
                        str(rel_path),
                        f"Utility flow '{flow_id}' has unusual on_complete.next_flow='{next_flow}'; expected 'return' or 'pause'",
                        "Consider using 'return' or 'pause' for utility flows",
                        file_path=str(graph_file)
                    )

        # Validation Rule 3: Utility flows should have flow_number >= 8
        if is_utility_flow and flow_number < 8:
            result.add_error(
                "UTILITY",
                str(rel_path),
                f"Utility flow '{flow_id}' has flow_number={flow_number}; utility flows should use 8+ (main SDLC flows use 1-7)",
                "Change flow_number to 8 or higher to indicate this is a utility flow",
                file_path=str(graph_file)
            )

        # Validation Rule 4: Main SDLC flows (1-7) should not have is_utility_flow=true
        if flow_number >= 1 and flow_number <= 7 and is_utility_flow:
            result.add_error(
                "UTILITY",
                str(rel_path),
                f"Flow '{flow_id}' (flow_number={flow_number}) is marked as utility flow but uses SDLC flow number (1-7)",
                "Either remove is_utility_flow from metadata, or change flow_number to 8+",
                file_path=str(graph_file)
            )

        # Validation Rule 5: If injection_trigger is defined but is_utility_flow is not true, warn
        if injection_trigger and not is_utility_flow:
            result.add_warning(
                "UTILITY",
                str(rel_path),
                f"Flow '{flow_id}' has injection_trigger='{injection_trigger}' but is_utility_flow is not true",
                "Add 'is_utility_flow: true' to metadata if this is a utility flow",
                file_path=str(graph_file)
            )

    return result
