## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-04-16 - [Path.rglob vs os.scandir Overhead]
**Learning:** Path.rglob("*") creates expensive `Path` objects for every file it encounters, causing significant overhead for large run directories. Replacing it with an iterative stack using `os.scandir` directly yields ~62% faster directory traversal because it avoids the abstraction overhead while still being safe and robust.
**Action:** Always prefer an iterative `os.scandir` stack over `Path.rglob` when frequently calculating metrics for deeply nested or large directories, especially when just summing stats where full path abstraction isn't necessary.
