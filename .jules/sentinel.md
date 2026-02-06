# Sentinel's Journal

## 2024-05-22 - Path Traversal in Spec Compiler Preview
**Vulnerability:** The `/api/station/compile-preview` endpoint used the `run_id` parameter directly to construct a file path without validation. This allowed path traversal (e.g., `../../etc`) which was then passed to `SpecCompiler`. While `SpecCompiler` mostly uses it for relative paths, the `user_prompt` in the output included the manipulated path, and potentially other artifacts could be accessed or trusted incorrectly.
**Learning:** `pathlib.Path` path construction does not automatically neutralize `..` components when one part comes from user input and is joined. Explicit validation is always required for user-supplied path components.
**Prevention:** Use `swarm.runtime.safe_paths.validate_path_component` for all user-supplied IDs that are used to construct file paths.
