## 2026-02-05 - Missing Path Validation in Event Streaming
**Vulnerability:** Path traversal in `stream_run_events` endpoint via unvalidated `run_id`.
**Learning:** `pathlib.Path` division operator (`/`) does not prevent path traversal (e.g., `base / "../secret"` resolves to parent). Explicit validation is required.
**Prevention:** Always use `validate_path_component` for any user-supplied ID used in file paths, even when using `pathlib`.
