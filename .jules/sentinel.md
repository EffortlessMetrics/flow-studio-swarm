
## 2024-05-09 - Path Traversal Vulnerabilities in API Endpoints

**Vulnerability:** Path traversal vulnerabilities identified in `evolution.py` and `wisdom.py` endpoints where user-supplied path components (`run_id`, `patch_id`, `artifact_name`) were used directly without validation. This allowed an attacker to bypass intended directory restrictions by providing paths like `../etc`.
**Learning:** While the system includes a path component validation utility (`validate_path_component`), it was not consistently applied to all path-related parameters in the Evolution and Wisdom APIs. FastAPI's `TestClient` normalizes paths, masking the absence of this validation during standard API tests.
**Prevention:**
1. Always validate all user-supplied path components using `validate_path_component` *before* utilizing them in any operations.
2. Ensure error handling raises an appropriate `HTTPException` (e.g., 400 Bad Request) when validation fails.
3. When testing path traversal scenarios in FastAPI, bypass `TestClient` and directly call the async endpoint functions to accurately test the application-level validation logic.
