## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2026-05-10 - Avoid Path.iterdir() for large directories
**Learning:** Using `Path.iterdir()` paired with `is_dir()` instantiates a `Path` object and forces a synchronous system `stat` call for every item, which is a significant performance bottleneck on large directories (e.g. 50k runs).
**Action:** Use `os.scandir()` instead, which efficiently returns OS-cached metadata like `entry.is_dir()` and `entry.name` for free. Only construct `Path` objects explicitly if needed by downstream code.
