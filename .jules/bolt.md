## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2026-03-23 - Faster Directory Traversal with os.scandir
**Learning:** When calculating directory sizes or deeply traversing a huge number of files, `pathlib.Path.rglob` is significantly slower because it incurs heavy object instantiation and path resolving overhead. `os.scandir` is highly optimized in C and avoids instantiating path objects.
**Action:** Use `os.scandir` with a recursive inner function (and `follow_symlinks=False` on `is_dir()` to avoid infinite loops) rather than `rglob` when pure traversal speed is critical.