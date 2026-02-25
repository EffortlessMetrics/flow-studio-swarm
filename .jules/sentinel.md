## 2025-02-18 - Path Traversal in Compile Preview
**Vulnerability:** The `CompilePreviewRequest` Pydantic model in `swarm/api/routes/compile.py` accepted an arbitrary `run_base` path string without validation, allowing path traversal attacks via `../` sequences. This could allow an attacker to direct the system to read or write files outside the intended directory.
**Learning:** Pydantic models do not automatically validate string fields for security (like path safety) unless explicit validators are added. Relying solely on type hints (`str`) is insufficient for security-critical inputs.
**Prevention:** Always use `@field_validator` with robust validation logic (like `validate_relative_path` or `validate_path_component`) for any field that will be used to construct file system paths.
