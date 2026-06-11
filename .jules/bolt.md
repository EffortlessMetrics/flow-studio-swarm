## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2024-03-22 - Optimize SpecManager.list_runs using os.scandir
**Learning:** `Path.iterdir()` can be surprisingly slow in directories with many items compared to `os.scandir()`.
**Action:** Replace `iterdir()` with `os.scandir()` and lexicographical sort when sorting large lists of items to optimize performance.

## 2024-03-22 - Leverage os.scandir cached stat attributes
**Learning:** While `os.scandir()` yields names faster than `Path.iterdir()`, its real performance power comes from its `DirEntry` objects caching `stat()` calls. Calling `Path.is_dir()` inside the processing loop defeats this purpose by invoking redundant system `stat` calls.
**Action:** When using `os.scandir()`, evaluate `.is_dir()` (or other stats) directly on the `DirEntry` object during the initial comprehension or loop, not later on constructed `Path` objects.
