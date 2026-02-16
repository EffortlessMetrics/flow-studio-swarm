## 2026-02-16 - Path Traversal in API Endpoints
**Vulnerability:** Path traversal in `CompilePreviewRequest` (run_base) and `stream_run_events` (run_id) allowing potential file access/reflection outside intended directories.
**Learning:** `pathlib.Path` does not prevent path traversal (e.g., `..`). API inputs used directly in path construction were assumed safe or not validated.
**Prevention:** Use `validate_path_component` for single components (IDs) and `validate_relative_path` for paths that must stay within a root. Do not trust `Path(user_input)`.
