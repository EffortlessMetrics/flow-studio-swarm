## 2026-01-24 - Avoid pathlib.Path.rglob for Recursive Directory Size Calculation
**Learning:** `pathlib.Path.rglob` is slow for recursive directory size calculation due to the overhead of instantiating full `Path` objects for every file and directory traversed. This becomes a significant bottleneck when calculating the size of large directories like `runs/`.
**Action:** Use a recursive `os.scandir` implementation instead. By utilizing `os.DirEntry` objects, it completely avoids `Path` object instantiation overhead and significantly speeds up directory traversal, providing a large performance boost for directory size calculations.

## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.