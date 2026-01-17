# swarm/tools/validation/validators/flows/config_parser.py
"""Flow configuration parsing utilities.

Provides robust YAML parsing for flow config files without external dependencies.
Handles both indentation styles used across different flow configs.
"""

from pathlib import Path
from typing import Any, Dict, Optional


def parse_flow_config(flow_path: Path) -> Dict[str, Any]:
    """
    Parse a flow config YAML file (robust YAML parsing without external deps).

    Handles both indentation styles:
    - signal.yaml: steps at indent 0, fields at indent 2
    - build.yaml: steps at indent 2, fields at indent 4

    Returns:
        Dict with keys: id, title, description, steps, cross_cutting, errors
    """
    result: Dict[str, Any] = {
        "id": flow_path.stem,
        "title": "",
        "description": "",
        "steps": [],
        "cross_cutting": [],
        "errors": []
    }

    try:
        content = flow_path.read_text(encoding="utf-8")
        lines = content.split("\n")

        current_list: Optional[str] = None
        in_step = False
        in_agents_list = False  # Track when we're inside an agents list

        for i, line in enumerate(lines, start=1):
            line_stripped = line.strip()

            # Skip empty lines and comments
            if not line_stripped or line_stripped.startswith("#"):
                in_agents_list = False  # Reset agents flag on empty line
                continue

            # Get indentation level
            indent = len(line) - len(line.lstrip())

            # Top-level key: value (no leading spaces) - but not list items (- ...)
            if indent == 0 and ":" in line_stripped and not line_stripped.startswith("- "):
                key, value = line_stripped.split(":", 1)
                key = key.strip()
                value = value.strip()

                if key == "key":
                    result["id"] = value.strip("'\"")
                elif key == "title":
                    result["title"] = value.strip("'\"")
                elif key == "description":
                    result["description"] = value.strip("'\"")
                elif key == "steps":
                    current_list = "steps"
                    in_step = False
                    in_agents_list = False
                elif key == "cross_cutting":
                    current_list = "cross_cutting"
                    in_step = False
                    in_agents_list = False
                else:
                    current_list = None
                    in_step = False
                    in_agents_list = False

            # Top-level list items (indent 0): step or cross_cutting item
            elif indent == 0 and line_stripped.startswith("- "):
                item = line_stripped[2:].strip()
                in_agents_list = False

                if current_list == "steps":
                    # Check if this line has 'id:' directly (step start)
                    if ":" in item:
                        key, value = item.split(":", 1)
                        if key.strip() == "id":
                            step_id = value.strip().strip("'\"")
                            result["steps"].append({  # type: ignore[union-attr]
                                "id": step_id,
                                "agents": [],
                                "role": "",
                                "human_only": False,
                                "line": i
                            })
                            in_step = True
                elif current_list == "cross_cutting":
                    # cross_cutting items are just agent names
                    result["cross_cutting"].append(item.strip("'\""))  # type: ignore[union-attr]
                    in_step = False

            # List item at indent level 2: could be a step or agent
            elif indent == 2 and line_stripped.startswith("- "):
                item = line_stripped[2:].strip()

                if current_list == "steps":
                    if in_agents_list:
                        # This is an agent under agents:
                        if result["steps"]:
                            result["steps"][-1]["agents"].append(item.strip("'\""))  # type: ignore[union-attr,index]
                    elif ":" in item:
                        # Check if this is a step start (has 'id:')
                        key, value = item.split(":", 1)
                        if key.strip() == "id":
                            step_id = value.strip().strip("'\"")
                            result["steps"].append({  # type: ignore[union-attr]
                                "id": step_id,
                                "agents": [],
                                "role": "",
                                "human_only": False,
                                "line": i
                            })
                            in_step = True
                            in_agents_list = False
                        else:
                            # Some other field at indent 2, mark as in_step
                            in_step = True
                    else:
                        in_step = True
                        in_agents_list = False
                elif current_list == "cross_cutting" and not in_agents_list:
                    result["cross_cutting"].append(item.strip("'\""))  # type: ignore[union-attr]

            # Nested fields within a step (agents:, role:, id:, etc.)
            elif current_list == "steps" and in_step and ":" in line_stripped:
                key, value = line_stripped.split(":", 1)
                key = key.strip()
                value = value.strip()

                if key == "agents":
                    in_agents_list = True
                elif in_agents_list:
                    # We were in agents list but hit another key, so exit agents list
                    in_agents_list = False
                    if key == "role" and result["steps"]:
                        result["steps"][-1]["role"] = value.strip("'\"")  # type: ignore[union-attr,index]

                if key == "id" and result["steps"]:
                    result["steps"][-1]["id"] = value.strip("'\"")  # type: ignore[union-attr,index]
                elif key == "role" and result["steps"]:
                    result["steps"][-1]["role"] = value.strip("'\"")  # type: ignore[union-attr,index]
                elif key == "kind":
                    if value.strip("'\"") == "human_only" and result["steps"]:
                        result["steps"][-1]["human_only"] = True  # type: ignore[union-attr,index]

            # Agent list items within a step (indent 6 for build.yaml style, indent 2 for signal.yaml)
            elif line_stripped.startswith("- ") and current_list == "steps" and in_agents_list:
                if result["steps"]:
                    agent_name = line_stripped[2:].strip().strip("'\"")
                    result["steps"][-1]["agents"].append(agent_name)  # type: ignore[union-attr,index]

    except Exception as e:
        result["errors"].append(f"Parse error: {e}")  # type: ignore[union-attr]

    return result
