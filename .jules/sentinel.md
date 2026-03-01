## 2026-03-01 - Path Traversal Vulnerability in Wisdom and Evolution APIs
**Vulnerability:** User-supplied path parameters `run_id`, `artifact_name`, `patch_id`, etc. are directly concatenated into file paths in FastAPI route handlers (e.g. `get_wisdom_artifacts`, `get_wisdom_content`, `get_evolution_patch_details`) without proper validation.
**Learning:** Even if FastAPI normalizes standard `../` traversal sequences on the client-side, URL-encoded traversal sequences like `%5c` can bypass FastAPI's built-in path normalization, exposing OS-level path traversal.
**Prevention:** Strictly require application-level validation using `validate_path_component` from `swarm.runtime.safe_paths` for all path parameters to reject all slashes and traversal attempts.
