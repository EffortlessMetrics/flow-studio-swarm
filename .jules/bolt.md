## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2025-02-23 - Optimize Directory Traversal
**Learning:** `pathlib.Path.iterdir()` combined with `.is_dir()` instantiates Path objects and causes expensive synchronous system stat calls for every item, which is extremely slow on large directories.
**Action:** Use `os.scandir()` instead for efficient directory traversal, reading `.name` and `.is_dir()` directly from the `os.DirEntry` object to avoid unnecessary system calls.
