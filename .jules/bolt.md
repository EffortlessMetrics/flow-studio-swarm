## 2026-01-24 - [Defer IO Checks in Large Lists]
**Learning:** When listing items from a potentially large directory where we only need the top N items sorted by metadata (e.g., mtime), it is much faster to sort using cached metadata from `os.scandir` first, and *then* perform expensive checks (like `os.path.exists` on child files) only on the top candidates. This reduces IO syscalls from O(N) to O(limit).
**Action:** Always check if filtering can be deferred until after sorting when dealing with file system listings or expensive per-item checks.
