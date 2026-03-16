## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-01-24 - Efficient Recursive Directory Size Calculation
**Learning:** Using `pathlib.Path.rglob` is significantly slower than a recursive function using `os.scandir` for calculating recursive directory sizes.
**Action:** For performance-critical code computing directory sizes, replace `pathlib.Path.rglob` with `os.scandir` to avoid redundant stat calls, placing `try...except OSError` blocks around individual `stat()` and `is_dir()` calls, and strictly using `follow_symlinks=False` for `is_dir()` to avoid infinite loops during traversal while matching original `Path.stat()` behavior.
