## 2025-01-26 - API Path Traversal Risks
**Vulnerability:** Multiple API endpoints (`/api/runs/{id}/events`, `/api/db/ingest/{id}`, etc.) used `run_id` directly in file paths without validation.
**Learning:** FastAPI path parameters are not automatically validated against directory traversal or forbidden characters beyond basic URL decoding. The custom `validate_path_component` utility must be explicitly called for any path parameter used in file operations.
**Prevention:** Always import `validate_path_component` from `swarm.runtime.safe_paths` and call it on any ID (run_id, flow_id, etc.) that will be used to construct a `Path` object.
