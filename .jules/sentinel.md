## 2024-03-XX - Missing Path Validation on Wisdom/Evolution APIs
**Vulnerability:** Path traversal vulnerability in Wisdom and Evolution API endpoints via `run_id`, `patch_id`, and `artifact_name` parameters.
**Learning:** Even internal API routes need strict path validation if user-supplied parameters are used to construct file paths. `_validate_path_param` wrapper around `validate_path_component` standardizes error handling.
**Prevention:** Always use `validate_path_component` or a standard wrapper for path parameters used in filesystem operations.
