# Sentinel's Journal

## 2024-01-01 - Path Traversal in Run Artifacts
**Vulnerability:** Run artifacts (transcripts, receipts) were loaded by directly concatenating user-supplied `run_id`, `flow_key`, and `step_id` with `pathlib`, allowing path traversal via `..`.
**Learning:** `pathlib` does not sanitize `..` in path construction. User inputs used in file paths must be strictly validated against an allowlist.
**Prevention:** Enforce `swarm.runtime.safe_paths.validate_path_component` for all path parameters before use.
