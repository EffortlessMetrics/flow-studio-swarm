import sys
from pathlib import Path

# Add repo root to path so we can import swarm
sys.path.insert(0, str(Path.cwd()))

from swarm.runtime.storage import get_run_path, find_run_path, RUNS_DIR

# Create a mock run directory
(RUNS_DIR / "run1").mkdir(parents=True, exist_ok=True)
Path("secret.txt").write_text("secret")

print(f"RUNS_DIR: {RUNS_DIR.resolve()}")

# Test 1: Valid run
try:
    path = get_run_path("run1")
    print(f"Valid run path: {path}")
except ValueError as e:
    print(f"Valid run failed: {e}")

# Test 2: Traversal attempt via get_run_path
try:
    path = get_run_path("../secret.txt")
    print(f"Traversal path: {path}")
except ValueError as e:
    print(f"Traversal blocked: {e}")

# Test 3: Traversal attempt via find_run_path
path = find_run_path("../secret.txt")
if path:
    print(f"Find run path (traversal): {path}")
else:
    print("Find run path (traversal): None (Blocked)")

# Test 4: Traversal attempt via find_run_path to existing dir
path = find_run_path("..")
if path:
    print(f"Find run path (..): {path}")
else:
    print("Find run path (..): None (Blocked)")
