## 2025-02-18 - Path Traversal in Run ID
**Vulnerability:** Run ID and Flow Key parameters were used directly in path construction, allowing traversal via `../` or absolute paths.
**Learning:** `pathlib.Path` allows absolute paths in `join` operations (`/`) to reset the path root, and `..` to traverse up.
**Prevention:** Use `resolve()` and `is_relative_to()` to validate that the final path is within the intended base directory. Strip leading separators from user input.
