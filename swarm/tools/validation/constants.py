# swarm/tools/validation/constants.py
"""Validation constants and mappings."""

BUILT_IN_AGENTS = ["explore", "plan-subagent", "general-subagent"]
VALID_MODELS = ["inherit", "haiku", "sonnet", "opus"]
VALID_COLORS = ["red", "blue", "green", "yellow", "purple", "orange", "pink", "cyan"]

# Role family → expected color mapping
ROLE_FAMILY_COLOR_MAP = {
    "shaping": "yellow",
    "spec": "purple",
    "design": "purple",
    "implementation": "green",
    "critic": "red",
    "verification": "blue",
    "analytics": "orange",
    "reporter": "pink",
    "infra": "cyan",
}

# Exit codes per contract
EXIT_SUCCESS = 0
EXIT_VALIDATION_FAILED = 1
EXIT_FATAL_ERROR = 2
