## 2026-01-28 - Unvalidated Run ID Path Traversal
**Vulnerability:** Path traversal vulnerability in `swarm/api/routes/events.py` and `swarm/api/routes/db.py` where `run_id` was used directly in file path construction without validation.
**Learning:** Even when a centralized `SpecManager` exists and has validation, independent route handlers might bypass it and implement their own (insecure) file access logic.
**Prevention:** Always use `swarm.runtime.safe_paths.validate_path_component` when handling file path components from user input, especially in independent route handlers.
