## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2025-02-14 - Optimize Path.rglob() performance
**Learning:** Path.rglob() incurs high overhead from creating Path objects and tracking state. Using an iterative os.scandir approach provides a ~66% performance boost for calculating directory sizes because it yields lightweight DirEntry objects with cached metadata.
**Action:** Favor iterative os.scandir with a stack over rglob for large-scale directory traversal operations where only file statistics (like size) are needed.
