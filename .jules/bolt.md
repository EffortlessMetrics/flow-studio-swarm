## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2024-04-22 - [Optimize get_dir_size in runs_gc.py]
**Learning:** Using `Path.rglob("*")` for directory size calculation is surprisingly slow because it builds intermediate generator layers and object instantiations.
**Action:** Use an iterative `os.scandir` approach with a stack for file operations like `get_dir_size`, which is measurably faster (over 2x speedup).
