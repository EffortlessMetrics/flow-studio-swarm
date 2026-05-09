## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-05-09 - Avoid iterdir for Large Directory Scanning
**Learning:** `Path.iterdir()` combined with `.is_dir()` instantiates path objects and forces expensive synchronous system stat calls for every item. In large directories, this becomes a significant bottleneck.
**Action:** Use `os.scandir()` instead to efficiently access cached OS metadata like `entry.is_dir()` and `entry.name`, reducing directory traversal time by ~85%. When a `Path` is expected downstream, explicitly construct it from `entry.path`.
