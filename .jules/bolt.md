## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2025-02-28 - Optimize directory traversal with os.scandir
**Learning:** pathlib.Path.iterdir() is noticeably slower than os.scandir() when traversing large directories because it constructs Path objects and requires separate system stat calls for checks like .is_dir(). os.scandir caches these attributes.
**Action:** Use os.scandir() instead of Path.iterdir() when traversing directories, especially when performing simple type checks like .is_dir().
