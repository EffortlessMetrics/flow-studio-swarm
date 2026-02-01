## 2026-02-01 - Path Traversal in Database API
**Vulnerability:** Path traversal vulnerability in `/api/db/rebuild` and `/api/db/ingest/{run_id}` endpoints allowed accessing files outside the `runs` directory via manipulated `run_id`.
**Learning:** `ResilientStatsDB` and `StatsDB` wrappers do not perform input validation on `run_id`, assuming the caller (API layer) has already validated it. The API endpoints were missing this validation.
**Prevention:** Always validate path components (using `validate_path_component`) in the API layer before passing them to internal services, especially when they are used to construct file paths.
