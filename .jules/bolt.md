## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-04-16 - Optimize Directory Traversal in Runs GC
**Learning:** Path.rglob() can be significantly slower than a custom iterative os.scandir() implementation for computing total directory size.
**Action:** Replace Path.rglob() with an iterative stack using os.scandir(follow_symlinks=False) when traversing large directories like run logs.
