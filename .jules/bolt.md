## 2025-01-20 - Defer Syscalls in Scandir Loops
**Learning:** `os.scandir` + `os.path.exists` inside a loop is O(N) syscalls. Even with dentry cache, it adds overhead.
**Action:** When filtering/sorting a large list of files where only top K are needed:
1. Scan and collect cached metadata (mtime) using `DirEntry.stat()`.
2. Sort in memory.
3. Only perform expensive checks (`exists`, `read`) on the top K items.
