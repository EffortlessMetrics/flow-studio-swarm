## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-01-24 - Use os.scandir Instead of rglob for Directory Size
**Learning:** `Path.rglob` is slow for computing sizes of large or deeply nested directories. `os.scandir` is significantly faster. Placing `try...except OSError` blocks around individual `stat()` and `is_dir()` / `is_file()` calls, and using `follow_symlinks=False`, prevents errors from aborting the entire directory traversal.
**Action:** Use `os.scandir` over `Path.rglob` for recursively calculating directory size when performance matters.
