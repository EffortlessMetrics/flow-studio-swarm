## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-04-13 - Optimize Directory Traversal
**Learning:** Path.rglob() overhead can be significant on large directory trees due to internal generation of Path objects and recursive overhead.
**Action:** Use an iterative os.scandir() implementation with follow_symlinks=False to dramatically reduce execution time (~66% faster) when computing directory sizes.
