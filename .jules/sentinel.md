## 2025-01-20 - Path Traversal in Run Events
**Vulnerability:** Path traversal in `swarm/api/routes/events.py` via `run_id` parameter. `stream_run_events` endpoint and `write_event` utilities constructed file paths using `runs_root / run_id` without validation, allowing access to arbitrary files (if suffix matched) or directory probing.
**Learning:** Even if `validate_path_component` exists and is used in some services (like `SpecManager`), direct API endpoints implementation might bypass it if they reconstruct paths manually.
**Prevention:** Always validate path parameters before using them in file path construction. Use `swarm.runtime.safe_paths.validate_path_component` consistently across all endpoints handling file paths.
