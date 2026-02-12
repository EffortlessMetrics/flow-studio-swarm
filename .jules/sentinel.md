## 2025-02-12 - [Unvalidated Station Preview Run ID]
**Vulnerability:** Path traversal vulnerability in `api_station_compile_preview` where `run_id` was directly used to construct a file path without validation.
**Learning:** API endpoints that take identifiers used for filesystem access must always validate them, especially when they are optional parameters like `run_id` that might be overlooked. The `SpecCompiler` assumes safe inputs for paths.
**Prevention:** Use `validate_path_component` for all user-provided identifiers that are used as path components. Add security tests specifically for endpoints that handle file paths.
