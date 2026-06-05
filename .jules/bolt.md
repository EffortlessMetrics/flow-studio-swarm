## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2025-06-05 - Replacing iterdir with scandir
**Learning:** Replaced `pathlib.Path.iterdir()` chained with `.is_dir()` and `.exists()` checks with `os.scandir()`. `os.scandir` is much faster because it avoids instantiating path objects and stat calls by reusing cached OS metadata.
**Action:** Always favor `os.scandir` when traversing directories, especially when checking `entry.is_dir()`, as it's considerably faster.
