## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-01-23 - Optimize Recursive Directory Size Calculation
**Learning:** Using `Path.rglob` for recursively calculating directory size creates unnecessary overhead through object creation and redundant `stat()` calls.
**Action:** Use `os.scandir` in a recursive helper function passing `follow_symlinks=False` to `is_dir()` and omitting it for `is_file()` and `stat()` to minimize recursive directory traversal overhead.
