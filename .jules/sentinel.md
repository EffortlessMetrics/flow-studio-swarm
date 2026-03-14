## 2024-05-24 - Path Traversal vulnerabilities when joining paths
**Vulnerability:** Constructing paths like `runs_root / run_id` without validating `run_id` introduces a path traversal vulnerability. An attacker can set `run_id` to `../something` and read/write outside the expected directory.
**Learning:** `run_id` as a path parameter must be explicitly validated before constructing any file system path, particularly when dealing with FastAPI path parameters. Framework-level protections don't always protect `Path` objects joining.
**Prevention:** Always validate path parameters with `validate_path_component` from `swarm.runtime.safe_paths` at the very beginning of the function, before resolving or using the file system path.
