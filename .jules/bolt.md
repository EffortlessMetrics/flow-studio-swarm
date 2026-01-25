## 2026-01-24 - Delayed File Existence Checks in Directory Traversal
**Learning:** When listing recent items from large directories using `os.scandir`, performing `os.path.exists()` or `stat()` calls on every entry to validate them *before* sorting is a major bottleneck (O(N) syscalls).
**Action:** Collect candidates with cached metadata (like `st_mtime` from `DirEntry`), sort them first, and only perform expensive validation checks (like file existence) on the top `limit` results. This reduces syscalls from O(N) to O(limit) for the common case.
