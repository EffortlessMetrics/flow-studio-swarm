## 2026-01-28 - Path Traversal in Boundary Review
**Vulnerability:** Path traversal vulnerability in `GET /api/runs/{run_id}/boundary-review` via the `flow_key` parameter. This allowed reading arbitrary JSON files from the system if they were located in a `handoff` directory.
**Learning:** The `flow_key` was used directly in path construction (`run_base / flow_key / "handoff"`) without validation, bypassing the expectation that it should only be a simple directory name. While `run_id` was validated, `flow_key` was overlooked.
**Prevention:** Always validate all user-supplied input that is used in file system path construction, even if it seems like a secondary filter parameter. Use `validate_path_component` for all such inputs.
