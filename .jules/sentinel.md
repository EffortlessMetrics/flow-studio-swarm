## 2025-02-17 - Validate Path Components
**Vulnerability:** Path traversal vulnerabilities (user input used dynamically in file paths without proper validation).
**Learning:** The `run_id` parameter and `example_id` parameters were being passed around across multiple modules directly from user-supplied inputs and constructed into file paths.
**Prevention:** Always validate path components using `validate_path_component` from `swarm.runtime.safe_paths` as early as possible before constructing any paths.
