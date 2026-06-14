## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2024-06-14 - Replace Path.iterdir() with os.scandir()
**Learning:** `Path.iterdir()` incurs heavy overhead from `stat` calls during iteration when constructing `Path` objects. Over thousands of files (e.g. active run records), this dominates execution time. `os.scandir()` provides a 3.2x-9.2x speedup by returning lightweight `DirEntry` objects whose `is_dir()` methods and `name` attributes leverage cached stat information.
**Action:** When filtering or mapping contents of large directories based on name or type, use `os.scandir` instead of `Path.iterdir()`.
