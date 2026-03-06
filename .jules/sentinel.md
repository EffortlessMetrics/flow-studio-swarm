## 2025-02-23 - [Path Traversal in Evolution API Apply Endpoint]
**Vulnerability:** Path traversal in Evolution API where a composite ID `patch_id` formatted as `run_id:patch_id` in apply requests allowed malicious input to be parsed.
**Learning:** Even if the framework automatically rejects standard path traversals like `../`, URL-encoded or composite string attacks where two parts are split (`run_id, patch_id = request.patch_id.split(":", 1)`) can bypass the framework. Both extracted segments must be explicitly validated.
**Prevention:** Apply application-level path validation to every segment resulting from splitting a composite string before it is used to interact with the file system.
