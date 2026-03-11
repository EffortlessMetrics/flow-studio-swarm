## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2025-03-11 - Efficient Recursive Directory Size Calculation
**Learning:** `pathlib.Path.rglob("*")` is slow for calculating recursive directory sizes because it builds `Path` objects and can hit limits or be slower than traversing the tree directly.
**Action:** Use a recursive function with `os.scandir(dir_path)` and its `is_file(follow_symlinks=False)` / `stat(follow_symlinks=False)` / `is_dir(follow_symlinks=False)` methods instead of `rglob` when calculating directory sizes in Python to significantly boost speed.