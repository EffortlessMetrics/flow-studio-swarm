## 2025-03-03 - [Path Traversal in Evolution API]
**Vulnerability:** User-supplied `run_id` and `patch_id` path parameters in the Evolution API (`swarm/api/routes/evolution.py`) were directly used in file system paths without validation, allowing potential path traversal.
**Learning:** FastAPI route handlers do not automatically prevent path traversal for directory traversal characters mapped within parameters (such as %5c or complex nested paths). All path components must be explicitly validated.
**Prevention:** Always use `swarm.runtime.safe_paths.validate_path_component(param, "param_name")` at the beginning of the route handler to explicitly validate path components before using them in filesystem operations. Catch `ValueError` and raise a 400 `HTTPException`.
