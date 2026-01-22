# Bolt's Journal

## 2025-01-22 - [Optimizing Directory Traversal]
**Learning:** `os.scandir()` is significantly faster than `pathlib.Path.iterdir()` for iterating over directories, especially when you need file attributes like `is_dir()` or `stat()`. `iterdir()` creates `Path` objects for every entry, which adds overhead. `scandir()` returns `DirEntry` objects which are lighter and cache stat results.
**Action:** Use `os.scandir()` for performance-critical directory traversal, especially when filtering by type or checking attributes.
