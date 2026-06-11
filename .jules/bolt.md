## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-06-11 - Optimize directory iteration with os.scandir
**Learning:** Using `pathlib.Path.iterdir()` instantiates an object for every entry, which creates significant overhead for thousands of run directories. Furthermore, running `.is_dir()` on all entries forces a stat call per directory. Sorting string names with `os.scandir()` and deferring existence checks inside a limited subset is significantly faster and saves I/O.
**Action:** When iterating and sorting a large directory without needing file metadata immediately, utilize `os.scandir()` to collect and sort string names, deferring any `.is_dir()` or `.stat()` calls strictly to the elements you process.
