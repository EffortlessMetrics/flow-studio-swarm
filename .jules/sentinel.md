## 2026-01-29 - API Path Traversal Validation Gap
**Vulnerability:** API endpoints accepting `run_id` (like `events` and `db` routes) constructed file paths directly using `pathlib` without validation, allowing path traversal.
**Learning:** `pathlib` operations (like `/`) do not automatically prevent traversal (e.g. `..`). FastAPIs `TestClient` normalizes paths, masking traversal issues in simple path-parameter tests.
**Prevention:** Always use `swarm.runtime.safe_paths.validate_path_component` for any user-controlled input used in file system operations.
