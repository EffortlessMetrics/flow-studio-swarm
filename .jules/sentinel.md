# Sentinel Journal

This log records CRITICAL security learnings.

## 2025-02-14 - Path Traversal in Run Events API
**Vulnerability:** The `stream_run_events` and `ingest_run_events` endpoints used the `run_id` parameter directly to construct file paths without validation, allowing path traversal (e.g., `../sensitive_file`).
**Learning:** Even if internal services (like `RunStateManager`) validate IDs, direct file system access in API endpoints must independently validate all path parameters. `pathlib` resolving paths does not prevent traversal if the root is just a prefix.
**Prevention:** Always use `validate_path_component` on any user input used to construct file paths, especially in endpoints that bypass high-level service layers.
