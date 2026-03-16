## 2024-05-24 - API Route Path Traversal Mitigation
**Vulnerability:** API routes (like `/wisdom/{run_id}` and `/runs/{run_id}/events`) used `run_id` as a string directly to construct local file system paths without validation, risking path traversal attacks.
**Learning:** Even though FastAPI routes path parameters properly in terms of framework constraints, application-level variables used to load/save files must be independently sanitized using `validate_path_component` when resolving paths via standard pathlib, otherwise arbitrary file reading or writing might occur.
**Prevention:** Consistently apply `validate_path_component` to all dynamically-sourced path parameters (`run_id`, `flow_id`, `station_id`, etc.) across all endpoints to prevent unsanitized payload paths.
