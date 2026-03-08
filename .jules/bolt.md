## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2024-05-24 - Efficient Directory Traversal and Lazy Evaluation
**Learning:** When evaluating large numbers of directories, eagerly computing sizes using `pathlib.Path.rglob` is a performance bottleneck due to generator overhead and repeated stat calls. Delaying this calculation and using `os.scandir` recursively improves performance dramatically.
**Action:** Use `os.scandir` for recursive size calculations and defer evaluation via `@property` and `dataclasses.field(default=-1, repr=False)` until the value is actually required.
