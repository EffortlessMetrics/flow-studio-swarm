# Sentinel's Journal

## 2026-01-20 - Path Traversal in Compile Preview
**Vulnerability:** `CompilePreviewRequest` in `swarm/api/routes/compile.py` accepted an unvalidated `run_base` path. This could allow path traversal if these paths were used for file operations or if the preview revealed sensitive file paths.
**Learning:** Even "preview" endpoints that appear to just display paths can be dangerous if they reflect user input without validation. The `run_base` parameter was used to construct paths shown in the prompt, which could be misleading or exploited if the system later used these paths.
**Prevention:** Always validate user-supplied path components using `validate_path_component` or `validate_relative_path`. I added `validate_relative_path` to `swarm/runtime/safe_paths.py` to safely handle relative paths without traversal.
