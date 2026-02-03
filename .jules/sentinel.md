## 2025-01-20 - [Path Traversal in Evolution Routes]
**Vulnerability:** Found that `swarm/api/routes/evolution.py` used `run_id` and `patch_id` to construct file paths without validation, allowing path traversal (e.g., checking for existence of arbitrary `.../wisdom` directories).
**Learning:** `replace_with_git_merge_diff` can apply changes to multiple locations if the context is identical; verify the application scope. Also, some endpoints perform initialization (like `get_spec_manager`) that must be mocked in unit tests to avoid runtime errors.
**Prevention:** Always use `validate_path_component` on any user input used for file path construction. Add specific tests for path traversal on all API endpoints that handle file paths.
