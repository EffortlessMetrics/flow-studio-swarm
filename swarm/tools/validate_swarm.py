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

from swarm.tools.validation.cli import main

if __name__ == "__main__":
    main()
