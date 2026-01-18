## 2025-02-12 - Path Traversal Vulnerability in Run Storage
**Vulnerability:** Found a Path Traversal vulnerability in `swarm/runtime/storage.py` within `get_run_path` and `find_run_path`. These functions accepted a `run_id` (e.g., `../../secret.txt`) and concatenated it with a base directory (`RUNS_DIR` or `EXAMPLES_DIR`) without validation. This allowed an attacker to potentially access files outside the intended directories if they could control the `run_id`.

**Learning:** `pathlib.Path`'s `/` operator or simple concatenation does not prevent traversal sequences (`..`). Even checking `exists()` or `is_dir()` on the resulting path is not sufficient security, as it confirms existence of files/dirs outside the sandbox. Explicit validation is required to ensure the resolved path remains within the intended root.

**Prevention:** Always resolve the final path using `.resolve()` and check if it is relative to the intended base directory using `.is_relative_to()` (or checking `parents` if Python < 3.9). Do not rely on string prefixes alone (`startswith`) as it can be vulnerable to "prefix attacks" (e.g., `/var/www` matching `/var/www_backup`).

**Fix Implementation:**
```python
    path = (runs_dir / run_id).resolve()
    runs_dir_resolved = runs_dir.resolve()
    if not path.is_relative_to(runs_dir_resolved):
        raise ValueError(f"Invalid run_id '{run_id}': Path traversal detected")
    return path
```
