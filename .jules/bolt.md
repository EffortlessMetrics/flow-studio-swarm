## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-04-19 - Iterative os.scandir faster than Path.rglob
**Learning:** In Python, `os.scandir` used with an iterative stack and `follow_symlinks=False` is significantly faster (~2x) than `Path.rglob("*")` for directory traversal because it avoids instantiating `Path` objects and fetching redundant stat data.
**Action:** Prefer iterative `os.scandir` over `Path.rglob` when recursively processing large directory structures for pure metadata tasks like calculating total sizes.
