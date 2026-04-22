## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-01-23 - Path.rglob Overhead
**Learning:** Path.rglob("*") is noticeably slower (~3x) than a custom iterative os.scandir approach for large directories, primarily due to the overhead of instantiating full Path objects for every single file in the hierarchy when you only need standard stats.
**Action:** For performance-critical tree traversals (like directory size calculation or garbage collection of thousands of runs), prefer an iterative stack using os.scandir with follow_symlinks=False over Path.rglob("*").
