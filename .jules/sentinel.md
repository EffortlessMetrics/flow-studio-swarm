## 2025-01-26 - Path Traversal in API Endpoints
**Vulnerability:** Unvalidated `run_id` and `patch_id` parameters in FastAPI endpoints allowed path traversal (e.g., `../etc/passwd`) when constructing file paths.
**Learning:** `pathlib.Path` does NOT automatically neutralize `..` components when used with `/` operator. Explicit validation is required before using user input in file paths.
**Prevention:** Always use `swarm.runtime.safe_paths.validate_path_component` for any user-controlled string used to construct filesystem paths.
