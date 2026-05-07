## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-05-07 - Use os.scandir for Fast Traversal
**Learning:** Checking `is_dir()` and string names over massive directories via `Path.iterdir()` evaluates path objects synchronously and hits system stat calls inefficiently. Even simply sorting path directories scales poorly to large folders like 50k run entries.
**Action:** Extract entries using `os.scandir` combined with `entry.name` directly in `list_runs` to minimize IO bottleneck.
