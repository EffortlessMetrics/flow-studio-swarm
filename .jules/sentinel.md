## 2024-05-18 - Path Validation in API Routes
**Vulnerability:** Path traversal vulnerability in API endpoints (e.g., `facts.py`).
**Learning:** Application-level path validation (like `validate_path_component`) must be applied explicitly at the beginning of API route handlers. Relying on lower-level functions like `find_run_path` to catch traversal isn't enough because framework-level URL normalization doesn't protect against encoded traversal payloads (e.g. `..%5Cetc%5Cpasswd`).
**Prevention:** Always validate path components derived from user input at the route level using `validate_path_component` (or similar) immediately after receiving them and before any file system or database operations, catching the resulting `ValueError` to return a well-formatted 400 error.
