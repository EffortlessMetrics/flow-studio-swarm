# Sentinel's Journal

## 2025-02-26 - [Path Traversal in Flow Key Parameter]
**Vulnerability:** Path traversal vulnerability in `swarm/api/routes/boundary.py:get_boundary_review`. The `flow_key` parameter was used directly in file path construction without validation. An attacker could supply `../secret` or an absolute path to access arbitrary files or traverse directories outside the intended run directory.
**Learning:** Even internal-sounding parameters like `flow_key` (which map to directory names) must be validated. `pathlib.Path`'s `/` operator will discard the left-hand side if the right-hand side is an absolute path, making strict validation critical.
**Prevention:** Always validate user-supplied path components using `validate_path_component` (or similar allowlist-based validation) before using them in file system operations. Ensure that no path component can be interpreted as an absolute path or traversal sequence.
