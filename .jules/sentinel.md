## 2026-03-01 - Path Traversal Vulnerability in Wisdom/Evolution API
**Vulnerability:** Missing path validation on user-supplied 'run_id', 'patch_id', and 'artifact_name' variables passed into FastAPI route handlers in 'evolution.py' and 'wisdom.py'. An attacker could use directory traversal characters (like '..') to interact with unintended directories or files.
**Learning:** Even internal API endpoints that typically receive well-formed IDs from the UI need defense-in-depth on user-provided URL and body parameters to prevent arbitrary file access or writing.
**Prevention:** Always validate and sanitize user-provided variables used in file system paths by enforcing strict character allow-listing (e.g., using 'validate_path_component') before concatenating them with base directories.
