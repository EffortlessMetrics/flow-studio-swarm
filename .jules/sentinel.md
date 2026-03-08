## 2026-03-08 - Path Traversal in File/Artifact APIs

**Vulnerability:** Path traversal (CWE-22) in `/wisdom` and `/evolution` API endpoints due to user-controlled inputs (`run_id`, `patch_id`, `artifact_name`) directly being concatenated to file paths using `Path(root) / user_input` without validation. Attackers could bypass directory restrictions by passing sequences like `../` to access files anywhere on the host system.

**Learning:** `pathlib.Path` in Python resolves directory traversals effectively internally, but does not prevent an attacker from breaking out of the intended root directory. Simply relying on path construction does not provide boundary security.

**Prevention:** Always validate path components and IDs derived from user requests before resolving file paths. Use `swarm.runtime.safe_paths.validate_path_component` to ensure that input contains no directory traversal sequences (`..`, `/`, `\`) and strictly represents a single directory or file name. Fail securely by catching `ValueError` and raising an `HTTPException` with a `400 Bad Request` status code.