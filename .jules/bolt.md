## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2025-03-09 - O(N) stat() Calls in pathlib.Path.iterdir()
**Learning:** In Python, `pathlib.Path.iterdir()` chained with `.is_dir()` instantiates a `Path` object for every directory entry, forcing a synchronous `stat()` system call per item. When used to enumerate large runtime directories (e.g., `swarm/runs/`), this creates a severe performance bottleneck.
**Action:** Replace `Path.iterdir()` loops with `os.scandir()`, which efficiently yields cached OS metadata (like `entry.is_dir()`) without executing individual `stat()` operations. When returning a limited subset of paths or sorting, filter/sort based on string values first, then conditionally construct `Path` objects only for the necessary items.
