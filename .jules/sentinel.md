## 2025-05-22 - Path Traversal in Flow Studio
**Vulnerability:** Run ID, Flow Key, and Step ID path parameters were unvalidated and used directly in file path construction, allowing traversal via `..`.
**Learning:** `pathlib`'s `/` operator does not resolve `..`, nor does it raise an error. It constructs a path that might point outside the intended directory if passed to file operations. FastAPI path parameters accept almost anything.
**Prevention:** Use strict allow-list validation (alphanumeric + safe chars) for all user-supplied identifiers used in file paths. Created `swarm.runtime.safe_paths.validate_path_component` for this purpose.
