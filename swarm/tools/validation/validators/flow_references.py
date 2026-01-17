# swarm/tools/validation/validators/flow_references.py
"""
FR-003: Flow References Validation

Validates that all agent references in flow specs are valid.
Uses Levenshtein distance for typo detection and suggestions.

Checks:
- Agent exists in registry or is a built-in
- Suggests similar names for potential typos
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

from swarm.validator import ValidationResult
from swarm.tools.validation.helpers import ROOT, FLOW_SPECS_DIR
from swarm.tools.validation.constants import BUILT_IN_AGENTS


def levenshtein_distance(s1: str, s2: str) -> int:
    """
    Calculate Levenshtein edit distance between two strings.

    Used for typo detection in agent references.
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


def parse_flow_spec_agents(flow_path: Path) -> List[Tuple[int, str]]:
    """
    Parse agent references from flow spec.

    Looks for patterns like:
    - Agent: `agent-name`
    - Step tables with agent columns
    - Inline references to agents

    Returns list of (step_number, agent_name) tuples.
    """
    agents: List[Tuple[int, str]] = []
    content = flow_path.read_text(encoding="utf-8")
    lines = content.splitlines()

    # Pattern 1: Agent: `agent-name`
    agent_ref_pattern = re.compile(r"Agent:\s*`([a-zA-Z0-9_\-]+)`")

    # Pattern 2: Look in step tables
    in_table = False

    for i, line in enumerate(lines, start=1):
        # Check for agent references
        match = agent_ref_pattern.search(line)
        if match:
            agent_name = match.group(1)
            agents.append((i, agent_name))

        # Check step tables (| Step | Node | Type |)
        if "| Step" in line and "Node" in line and "Type" in line:
            in_table = True
            continue

        if in_table:
            if line.startswith("|---"):
                continue
            if not line.startswith("|"):
                in_table = False
                continue

            cols = [c.strip() for c in line.strip("|").split("|")]
            if len(cols) >= 3:
                try:
                    step = int(cols[0])
                    node = cols[1].strip()
                    node_type = cols[2].strip()

                    # Extract agent name from backticks
                    if node.startswith("`") and node.endswith("`"):
                        node = node[1:-1]

                    # Only track 'agent' type nodes
                    if node_type == "agent":
                        agents.append((step, node))
                except (ValueError, IndexError):
                    pass

    return agents


def validate_flow_references(registry: Dict[str, Dict[str, Any]]) -> ValidationResult:
    """
    Validate that all agent references in flow specs are valid.

    Checks:
    - Agent exists in registry or is a built-in
    - Suggests typos using Levenshtein distance
    """
    result = ValidationResult()

    if not FLOW_SPECS_DIR.is_dir():
        return result

    # Build list of valid agent names
    valid_agents = set(registry.keys()) | set(BUILT_IN_AGENTS)
    candidate_list = list(valid_agents)

    for flow_path in sorted(FLOW_SPECS_DIR.glob("flow-*.md")):
        if flow_path.is_symlink():
            # Skip symlinks: validation only applies to real files
            continue

        rel_path = flow_path.relative_to(ROOT)
        agent_refs = parse_flow_spec_agents(flow_path)

        for line_num, agent_name in agent_refs:
            if agent_name not in valid_agents:
                # Find similar names
                suggestions = suggest_typos(agent_name, candidate_list)

                location = f"{rel_path}:line {line_num}"

                if suggestions:
                    problem = f"references unknown agent '{agent_name}'; did you mean: {', '.join(suggestions)}?"
                    fix_action = f"Update reference to one of: {', '.join(suggestions)}, or add '{agent_name}' to swarm/AGENTS.md"
                else:
                    problem = f"references unknown agent '{agent_name}'"
                    fix_action = f"Add '{agent_name}' to swarm/AGENTS.md, or fix the agent name"

                result.add_error(
                    "REFERENCE",
                    location,
                    problem,
                    fix_action,
                    line_number=line_num,
                    file_path=str(flow_path)
                )

    return result
