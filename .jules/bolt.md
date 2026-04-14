## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-04-14 - [Optimize get_dir_size in runs_gc.py]
**Learning:** Path.rglob('*') is significantly slower than os.scandir for directory traversal, especially when computing directory sizes where many files exist.
**Action:** Replaced Path.rglob('*') with an iterative os.scandir implementation, reducing execution time by ~57%.
