## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2024-03-26 - Directory Traversal Performance
**Learning:** When calculating total directory size recursively, using `os.scandir` directly with an iterative stack is significantly faster than using `pathlib.Path.rglob` because it avoids building intermediate objects and fetches stats directly.
**Action:** Use `os.scandir` instead of `Path.rglob` for recursive directory size calculations when performance is critical.