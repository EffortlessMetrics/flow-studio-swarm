## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-03-11 - Use `os.scandir` instead of `pathlib.Path.rglob` for efficient directory traversal
**Learning:** `pathlib.Path.rglob` is slow for calculating recursive directory sizes because it instantiates `Path` objects and performs excessive stat calls. `os.scandir` is much faster because it iterates at the C level and caches file attributes.
**Action:** When calculating recursive directory sizes, prefer a recursive function using `os.scandir` over `pathlib.Path.rglob`. Ensure `follow_symlinks=False` is used to prevent infinite loops, double-counting, and aborted traversal on broken symlinks.
