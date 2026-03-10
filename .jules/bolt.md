## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-01-24 - Optimize Recursive Directory Size Calculation
**Learning:** `pathlib.Path.rglob` can be significantly slower than `os.scandir` for recursive directory size calculation due to object instantiation and internal checks.
**Action:** Use `os.scandir` recursively with `follow_symlinks=False` inside a `try...except OSError` loop for fast and robust recursive directory size calculations.
