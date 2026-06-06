## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-06-06 - Optimize large directory traversal using os.scandir
**Learning:** Using `Path.iterdir()` with `.is_dir()` on large directories instantiates Path objects and forces expensive synchronous system stat calls for every item.
**Action:** Use `os.scandir()` to efficiently access cached OS metadata like `entry.is_dir()` and `entry.name`. Evaluate `entry.is_dir()` and `entry.name` directly on the `os.DirEntry` object before converting it to a `Path` object to avoid negating the performance benefits with new system calls.
