## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2024-05-24 - Optimize large directory scanning
**Learning:** `pathlib.Path.iterdir()` is a significant performance bottleneck on large directories because it instantiates Path objects for every entry before sorting. `os.scandir()` within a context manager avoids instantiating objects for all items.
**Action:** When scanning large directories, extract and sort lightweight string names via `os.scandir()` first, then instantiate Path objects only for the needed entries.
