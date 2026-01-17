# swarm/tools/validation/validators/flows/agent_validity.py
"""Flow agent validity validation.

Validates that all agent references in flow configurations point to
valid agents in the registry or built-in agent list.
"""

from typing import Any, Dict, List, Tuple

from swarm.validator import ValidationResult
from swarm.tools.validation.constants import BUILT_IN_AGENTS
from swarm.tools.validation.helpers import FLOWS_CONFIG_DIR


def levenshtein_distance(s1: str, s2: str) -> int:
    """
    Calculate the Levenshtein distance between two strings.

    Uses dynamic programming for O(m*n) time complexity.
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row: list[int] = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row: list[int] = [i + 1]
        for j, c2 in enumerate(s2):
            # Cost of insertions, deletions, or substitutions
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def suggest_typos(name: str, candidates: List[str], max_dist: int = 2) -> List[str]:
    """
    Suggest similar agent names using Levenshtein distance.

    Returns up to 3 suggestions with distance <= max_dist, sorted by distance.
    """
    suggestions: List[Tuple[int, str]] = []
    for candidate in candidates:
        dist = levenshtein_distance(name.lower(), candidate.lower())
        if dist <= max_dist:
            suggestions.append((dist, candidate))

    # Sort by distance, then alphabetically
    suggestions.sort(key=lambda x: (x[0], x[1]))

    # Return up to 3 suggestions
    return [s[1] for s in suggestions[:3]]


def validate_flow_agent_validity(
    flow_configs: Dict[str, Dict[str, Any]],
    registry: Dict[str, Dict[str, Any]]
) -> ValidationResult:
    """
    Validate that all agent references in flows are valid.

    Invariant 3: Agent validity - agents exist in registry
    """
    result = ValidationResult()

    # Build list of valid agents
    valid_agents = set(registry.keys()) | set(BUILT_IN_AGENTS)
    candidate_list = list(valid_agents)

    for flow_id, config in flow_configs.items():
        for step in config.get("steps", []):
            for agent in step.get("agents", []):
                if agent not in valid_agents:
                    flow_file = FLOWS_CONFIG_DIR / f"{flow_id}.yaml"
                    location = f"swarm/config/flows/{flow_id}.yaml"

                    # Find similar names
                    suggestions = suggest_typos(agent, candidate_list)

                    if suggestions:
                        problem = f"Flow '{flow_id}' step '{step['id']}' references unknown agent '{agent}'; did you mean: {', '.join(suggestions)}?"
                        fix_action = f"Update agent reference to one of: {', '.join(suggestions)}, or add '{agent}' to swarm/AGENTS.md"
                    else:
                        problem = f"Flow '{flow_id}' step '{step['id']}' references unknown agent '{agent}'"
                        fix_action = f"Add '{agent}' to swarm/AGENTS.md, or fix the agent name"

                    result.add_error(
                        "FLOW",
                        location,
                        problem,
                        fix_action,
                        file_path=str(flow_file),
                        line_number=step.get("line")
                    )

    return result
