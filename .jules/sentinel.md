## 2024-05-24 - API Routes Path Traversal Protection
**Vulnerability:** Path traversal vulnerabilities in `swarm/api/routes` due to missing input validation on user-supplied path parameters (`run_id`, `artifact_name`, `patch_id`, etc).
**Learning:** FastAPI route parameters are decoded and can be directly passed to file system operations (like `Path()`), bypassing frontend validation.
**Prevention:** We need a robust and reusable validation pattern. The user provided standard is `_validate_path_param` in `swarm/api/routes/validation_utils.py` handling `HTTPException` conversion from `validate_path_component`.
