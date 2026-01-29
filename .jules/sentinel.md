# Sentinel's Journal

## 2025-01-28 - Path Traversal in Run ID
**Vulnerability:** Path traversal vulnerabilities were found in `swarm/api/routes/events.py` and `swarm/api/routes/db.py` where `run_id` was used to construct file paths without validation.
**Learning:** The vulnerability existed because these endpoints bypassed the standard `RunStateManager` service (which includes validation) and implemented direct filesystem access logic, missing the validation step.
**Prevention:** Enforce usage of centralized services (like `RunStateManager`) for all entity access instead of ad-hoc filesystem operations. Ensure all API inputs used in path construction are validated using `validate_path_component`.
