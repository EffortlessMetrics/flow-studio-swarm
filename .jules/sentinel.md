## 2025-01-20 - Unvalidated Run ID usage in StatsDB Rebuild

**Vulnerability:** `StatsDBRebuildMixin.rebuild_from_events` utilized `run_id` to construct file paths without validation, allowing path traversal. This was exposed via the `/db/ingest/{run_id}` and `/db/rebuild` endpoints.
**Learning:** While `storage.py` helpers often validate `run_id`, lower-level mixins or direct file access paths (like database rebuilding logic) might miss it. Mixing DB logic with file system logic requires strict input validation.
**Prevention:** Always use `swarm.runtime.safe_paths.validate_path_component` for any ID used in file path construction, especially in "backend" or "maintenance" methods that might be exposed via API.
