## 2024-05-22 - [Lazy File Existence Checks]
**Learning:** Optimizing `list_runs` by sorting `os.scandir` results by mtime *before* checking file existence reduced system calls from O(N) to O(limit) for the common case.
**Action:** Apply this pattern to any directory listing function where we only need the top K items and validity checks are expensive.
