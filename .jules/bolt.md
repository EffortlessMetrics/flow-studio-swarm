## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2025-06-14 - Defer File Existence Checks and Path object overhead
**Learning:** When scanning runs directories, using `Path.iterdir()` and repeatedly checking `Path.exists()` introduces measurable overhead. The `os.scandir` function caches file stats (like `st_mtime`) on the `DirEntry` object, allowing sorting candidates by mtime *before* instantiating expensive `Path` objects or hitting the filesystem again for `os.path.exists()` checks. This deferred evaluation is critical for large datasets.
**Action:** Replace `Path.iterdir()` with `os.scandir` combined with `os.path.exists` when sorting and filtering large lists of directories based on cached `stat` info and target files.
