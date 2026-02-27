## 2026-01-20 - API Path Traversal Prevention
**Vulnerability:** Path traversal vulnerabilities were identified in `wisdom` and `evolution` API endpoints where user-supplied parameters (`run_id`, `artifact_name`, `patch_id`) were used to construct file paths without sufficient validation.
**Learning:** FastAPI path parameters are not automatically validated against traversal or unsafe characters. Simply joining a user string to a `Path` object is unsafe if the string contains `..` or starts with `/`. While `pathlib` resolves `..`, it might still point outside the intended root if the input is malicious.
**Prevention:**
1.  Always use `validate_path_component` from `swarm.runtime.safe_paths` for any user input used in path construction.
2.  Use a strict allowlist regex (`^[a-zA-Z0-9_\-\.]+$`) to reject slashes, null bytes, and traversal sequences.
3.  Wrap validation calls in endpoints to catch `ValueError` and re-raise as `HTTPException(400)` for proper API error reporting.
4.  Add specific regression tests (`tests/test_security_api_endpoints.py` style) that attempt traversal and verify 400 Bad Request responses.
