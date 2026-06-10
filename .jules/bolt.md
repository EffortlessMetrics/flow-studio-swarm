## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-02-12 - Replaced pathlib.Path.iterdir() with os.scandir()
**Learning:** Found multiple places iterating over runs root that were using pathlib's iterdir() coupled with .is_dir(), which performs synchronous stat calls. This creates massive regressions when run over directories containing 50,000 runs. Refactoring them to use `os.scandir()` to extract cached `e.name` strings and only evaluate subset of the paths avoids the system calls on every entry.
**Action:** When filtering or sorting large directory listings based on file properties like is_dir(), replace pathlib.Path.iterdir() with os.scandir() and use the DirEntry attributes to fetch metadata efficiently before instantiating objects.
