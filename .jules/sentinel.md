## 2026-02-02 - Path Traversal in API Routes
**Vulnerability:** Path traversal in `db` and `evolution` API routes allowing access to files outside `runs_dir`.
**Learning:** `pathlib.Path` using `/` operator does not sanitize traversal sequences (e.g., `path / '../file'`). Strict validation of user inputs is required before joining paths.
**Prevention:** Always use `validate_path_component` from `swarm.runtime.safe_paths` for any user-controlled path component before using it in file operations.
