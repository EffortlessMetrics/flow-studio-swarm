# Sentinel's Journal

## 2025-02-14 - Path Traversal in SSE Endpoint
**Vulnerability:** Missing path validation in `stream_run_events` endpoint allowed potential path traversal via `run_id`.
**Learning:** `validate_path_component` is available but must be manually applied to every endpoint handling file paths. Automated scanners or centralized validation middleware would prevent this.
**Prevention:** Ensure all endpoints taking `run_id` call `validate_path_component`.
