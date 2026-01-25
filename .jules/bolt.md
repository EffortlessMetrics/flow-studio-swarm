
## 2025-02-17 - Double Directory Iteration in Run Service
**Learning:** `RunService.list_runs_paginated` was iterating the `runs/` directory twice (once for active runs, once for legacy runs) and performing redundant `stat` calls for `meta.json`.
**Action:** Use `storage.scan_runs()` which performs a single pass over the directory using `os.scandir` and classifies runs as active or legacy in one go. This reduces syscalls and iteration overhead. Always check for single-pass scan opportunities when handling mixed content in large directories.
