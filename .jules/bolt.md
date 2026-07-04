## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-01-23 - Fast Legacy Directory Traversal
**Learning:** Checking file existence or checking if a directory exists for multiple keys within a directory traversal loop (`os.scandir`) involves multiple expensive stat syscalls. Caching the directory entries with `os.listdir` and doing a set intersection is up to 2.5x faster when checking for multiple specific keys, significantly removing bottlenecks for discovery operations on thousands of folders.
**Action:** Always fetch the directory contents once as a set (`set(os.listdir())`) when needing to check for the presence of multiple potential children keys inside a directory traversal loop, rather than doing multiple `os.path.exists` or `os.path.isdir` calls.
