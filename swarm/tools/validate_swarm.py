#!/usr/bin/env python3
"""
validate_swarm.py - Swarm Alignment Validator

This file is a compatibility shim. The implementation has been modularized
and moved to swarm/tools/validation/.

See swarm/tools/validation/ for the full implementation.
"""

import sys
from pathlib import Path

# Add swarm package to path for library imports
_SWARM_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_SWARM_ROOT) not in sys.path:
    sys.path.insert(0, str(_SWARM_ROOT))

from swarm.tools.validation.cli import main  # noqa: E402
from swarm.tools.validation.validators.flow_references import (  # noqa: E402
    levenshtein_distance,
    parse_flow_spec_agents,
    suggest_typos,
)
from swarm.tools.validation.validators.runbase import validate_runbase_paths  # noqa: E402

# Re-export public API for backward compatibility
# Tests and other code may import from this shim
from swarm.validator import SimpleYAMLParser, ValidationError, ValidationResult  # noqa: E402

__all__ = [
    "SimpleYAMLParser",
    "ValidationError",
    "ValidationResult",
    "levenshtein_distance",
    "parse_flow_spec_agents",
    "suggest_typos",
    "validate_runbase_paths",
    "main",
]

if __name__ == "__main__":
    main()
