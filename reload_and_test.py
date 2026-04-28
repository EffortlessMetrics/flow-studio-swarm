import sys
import importlib

# Reload module to ensure the newly generated HTML is loaded
import swarm.tools.flow_studio_ui
importlib.reload(swarm.tools.flow_studio_ui)

import pytest
sys.exit(pytest.main(["tests/test_flow_studio_ui_ids.py"]))
