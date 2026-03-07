
## 2025-02-12 - Path Traversal in Wisdom and Evolution APIs
**Vulnerability:** Path traversal vulnerabilities found in `swarm/api/routes/wisdom.py` and `swarm/api/routes/evolution.py` where user-supplied path variables (`run_id`, `artifact_name`, `patch_id`) were not being validated before being used to construct filesystem paths.
**Learning:** Framework-level path sanitization (like FastAPI's `../` normalization via `TestClient`) often masks missing application-level validation. When taking path parameters from an API, it's essential to validate the separated string segments explicitly before resolving them as `pathlib.Path` objects.
**Prevention:** Apply the `validate_path_component` function from `swarm.runtime.safe_paths` to explicitly validate all path components derived from user input before filesystem resolution, and ensure test clients bypass high-level normalization to assert the app-level 400 rejection logic correctly functions.
