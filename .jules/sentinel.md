
## 2025-02-13 - Path Traversal Vulnerability in Evolution API
**Vulnerability:** Path traversal vulnerability in Evolution API endpoints (`/evolution/apply`, `/evolution/reject`, etc.) where user-supplied `patch_id` and `run_id` inputs were used without prior validation to construct file system paths (e.g., `runs_root / run_id / "wisdom" / f".rejected_{patch_id}"`).
**Learning:** Framework-level sanitization via `TestClient` paths normalizes path strings like `../` to application-level structures. However, composite strings containing directory traversal sequences passed within JSON request payloads (e.g., `{"patch_id": "../etc:patch_id"}`) mask validation logic and bypass normalizations entirely.
**Prevention:** Always apply explicit, application-level path validation using a validated component extraction mechanism (like `swarm.runtime.safe_paths.validate_path_component`) to individual split segments of string components before utilizing them for arbitrary file system resolution.
