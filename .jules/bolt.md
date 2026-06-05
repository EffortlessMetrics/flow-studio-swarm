## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-01-23 - Performance optimization: os.scandir over iterdir
**Learning:** Using `pathlib.Path.iterdir()` paired with `is_dir()` and string manipulation causes unnecessary `stat` calls and path object constructions. `os.scandir` accesses the OS metadata directly without making stat calls, which provides an efficient way to check if an entry is a directory and access its name.
**Action:** When filtering or looping through entries in a directory, use `os.scandir` instead of `iterdir` to avoid creating multiple `Path` objects and making redundant stat calls.
