## 2025-01-20 - [CRITICAL] Path Traversal in API Endpoints
**Vulnerability:** Found unvalidated `run_id` parameters in `stream_run_events` and database management endpoints used to construct file paths.
**Learning:** `validate_path_component` was available but missed in some API routes, likely due to manual implementation of path construction instead of using a central manager or validator.
**Prevention:** Enforce `validate_path_component` usage for all path parameters in API routes via linting or review checklists.
