## 2024-05-23 - Path Traversal Prevention
**Vulnerability:** API endpoints in `runs.py` and artifact loaders in `run_artifacts.py` used `run_id`, `flow_key`, and `step_id` directly in file paths without strict validation, potentially allowing path traversal attacks via `../` or similar patterns.
**Learning:** `pathlib.Path` does not prevent path traversal when joining user-controlled strings (e.g. `base / "../etc/passwd"` resolves to `/etc/passwd`). Explicit validation is necessary.
**Prevention:** Created `swarm/runtime/safe_paths.py` with `validate_path_component` enforcing a strict allowlist (alphanumeric, `_`, `-`, `.`) and explicitly rejecting `..`. Applied this validation at API boundaries and service layers.
