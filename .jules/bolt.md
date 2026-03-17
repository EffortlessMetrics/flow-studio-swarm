## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2026-03-17 - Recursive Directory Traversal with os.scandir and Lazy Evaluation
**Learning:** `pathlib.Path.rglob` is significantly slower than using a recursive function with `os.scandir` when determining directory sizes for many runs, particularly because gathering unnecessary metadata upfront slows down discovery.
**Action:** Use `os.scandir` for recursive size calculations and compute properties lazily using a cached backing field (`@property` combined with a `_field: int | None = None`) so sizes are only calculated when explicitly accessed.