## 2026-01-27 - [Sentinel Path Traversal Fix]
**Vulnerability:** Path Traversal in API endpoints
**Learning:** API endpoint parameters were directly interpolated into file paths without proper validation.
**Prevention:** Use `validate_path_component` utility function for user-supplied string inputs before interacting with paths.
