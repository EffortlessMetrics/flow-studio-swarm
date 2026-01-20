## 2025-05-15 - Path Traversal in Run Artifacts
**Vulnerability:** Path traversal in `run_id`, `flow_key`, and `step_id` inputs allowed accessing files outside `runs/` directory via `..`.
**Learning:** `pathlib` path joining (`/`) does not prevent traversal like `..`. Web frameworks might block it in URL paths, but not if passed as parameters or encoded.
**Prevention:** Always validate user-provided path components using a strict allowlist (alphanumeric + safe chars) and explicitly reject `..`. Added `swarm.runtime.safe_paths.validate_path_component`.
