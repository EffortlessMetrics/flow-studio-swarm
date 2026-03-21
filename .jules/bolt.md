## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2024-03-21 - Optimize Directory Size Calculation
**Learning:** Using `pathlib.Path.rglob` to traverse directories and calculate total size is slow due to the creation of intermediate Path objects and the overhead of resolving globs.
**Action:** For performance-critical recursive directory traversal, especially when calculating sizes of deep directories or directories with many files, use `os.scandir` with `is_dir(follow_symlinks=False)` to prevent infinite loops, and handle recursion manually to avoid Path object instantiation overhead.
