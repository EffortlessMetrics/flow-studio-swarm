## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-04-20 - Optimize get_dir_size in runs_gc.py
**Learning:** Path.rglob("*") creates significant overhead for basic file traversal compared to an iterative os.scandir implementation, yielding ~2.35x speedup.
**Action:** Use os.scandir for raw directory traversal when only file sizes/stats are needed.
