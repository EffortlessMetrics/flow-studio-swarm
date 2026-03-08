import time
import os
import shutil
from pathlib import Path

# Need to set up environment variables or mock the RUNS_DIR inside swarm/tools/runs_gc.py
import swarm.tools.runs_gc

# Let's mock it
swarm.tools.runs_gc.RUNS_DIR = Path("runs")
swarm.tools.runs_gc.EXAMPLES_DIR = Path("examples")

from swarm.tools.runs_gc import discover_all_runs

start = time.time()
runs = discover_all_runs()
end = time.time()
print(f"Discovered {len(runs)} runs in {end - start:.4f}s")
