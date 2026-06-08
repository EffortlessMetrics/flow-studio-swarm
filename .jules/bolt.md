## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-01-24 - Optimize directory iteration
**Learning:** `pathlib.Path.iterdir()` combined with `.is_dir()` instantiation is extremely slow for large directories since it creates many Path objects and forces synchronous syscalls.
**Action:** Use `os.scandir()` instead for iteration to efficiently access cached OS metadata, filtering entries before explicitly wrapping required results in `Path` objects.
