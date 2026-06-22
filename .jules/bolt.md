## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2025-06-22 - Optimize `iterdir()` in large run directories
**Learning:** `pathlib.Path.iterdir()` coupled with sorting (`sorted(path.iterdir())`) is surprisingly slow when there are hundreds or thousands of run directories, because it instantiates full `Path` objects for every single entry before sorting. `os.scandir()` provides a substantial performance boost by yielding lightweight `DirEntry` objects, allowing us to extract and sort strings instead.
**Action:** Always prefer `os.scandir()` over `iterdir()` when scanning and sorting large flat directories where we only need the directory names.
