## 2025-01-20 - [Optimizing Directory Traversal]
**Learning:** `os.scandir` and `os.path` functions are significantly faster (observed ~3.8x speedup) than `pathlib.Path.iterdir()` when iterating over thousands of directories, primarily due to avoiding `Path` object creation overhead and leveraging cached `stat` results from `scandir`.
**Action:** Prefer `os.scandir` for performance-critical file system iteration over large datasets.
