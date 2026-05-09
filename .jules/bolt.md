## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2025-02-23 - Optimize Large Directory Scans using os.scandir
**Learning:** Using `pathlib.Path.iterdir()` paired with `.is_dir()` and string sorting on large directories (like runs) requires instantiating numerous Path objects and invoking synchronous system stat calls for every entry. This drastically impacts performance.
**Action:** Instead, leverage `os.scandir()` to traverse the directory. It returns fast lightweight `os.DirEntry` objects whose `is_dir()` and `name` properties read from the OS's cached metadata buffer, eliminating redundant system stat calls. Only construct Path objects or fetch extra metadata on the top entries after filtering and sorting.
