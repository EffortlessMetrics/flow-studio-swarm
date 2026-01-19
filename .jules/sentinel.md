## 2025-05-15 - Path Traversal via Unsanitized Input
**Vulnerability:** User-supplied inputs (`run_id`, `flow_key`, `step_id`) were directly concatenated into file paths without validation, allowing for path traversal attacks.
**Learning:** `pathlib.Path` joining does not prevent traversal (e.g., `Path("/base") / "../etc"`) if the OS resolves it. Always validate input components before use.
**Prevention:** Use strict allowlisting (alphanumeric only) for file path components using `swarm.runtime.safe_paths.validate_path_component`.
