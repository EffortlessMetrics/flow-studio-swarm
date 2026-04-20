## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-04-20 - [Scandir Iterative Stack for Directory Traversal]
**Learning:** Path.rglob('*') can be significantly slower than a custom iterative stack with os.scandir for directory size calculations due to the overhead of creating Path objects for every file.
**Action:** When speed is critical and only basic file stats are needed, use an iterative os.scandir approach instead of rglob.
