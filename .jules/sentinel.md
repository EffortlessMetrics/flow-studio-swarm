## 2025-01-26 - API Path Traversal in Unvalidated Endpoints
**Vulnerability:** Path traversal vulnerability in `stream_run_events` (events.py) and multiple `wisdom.py` endpoints where `run_id` was used directly in path construction without validation.
**Learning:** Even when utility classes (like `RunStateManager`) have validation, endpoints that bypass them and access the filesystem directly must implement their own validation. Relying on shared utilities is safer than ad-hoc path construction.
**Prevention:** Always use `validate_path_component` or similar validators for any user input used in file paths. Audit all `APIRouter` endpoints that accept path parameters.
