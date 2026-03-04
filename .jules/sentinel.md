## 2024-05-24 - API Route Path Traversal Vulnerability
**Vulnerability:** Path traversal vulnerabilities exist in user-supplied path parameters (like `run_id`, `patch_id`, `artifact_name`) in FastAPI endpoints within `evolution.py` and `wisdom.py`.
**Learning:** FastAPI's default path normalization intercepts standard `../` traversal attempts but may pass URL-encoded characters (like `%5c`) directly to the route handler, allowing OS-level path traversal.
**Prevention:** Always validate user-supplied path parameters in FastAPI routes using `swarm.runtime.safe_paths.validate_path_component` and catch `ValueError` to raise an `HTTPException` with status code 400. For composite IDs like `run_id:patch_id`, split and validate both parts separately.
