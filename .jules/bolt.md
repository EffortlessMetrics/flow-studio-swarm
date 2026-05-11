## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-05-11 - Directory Traversal Performance
**Learning:** Sorting paths from `pathlib.Path.iterdir()` directly on large directories forces expensive and unnecessary `is_dir()` stat checks on all items.
**Action:** Use `os.scandir()` to extract directory names via cached OS metadata first (`e.is_dir()` and `e.name`), then sort strings, and finally construct `Path` objects only for the necessary top N results. This speeds up directory parsing significantly.
