## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-04-13 - Iterative os.scandir vs pathlib.rglob
**Learning:** pathlib.rglob has significant overhead due to Path object creation. Using an iterative os.scandir stack provides a 2.5x performance boost for large directory operations.
**Action:** Use os.scandir directly when traversing large directories where Path object convenience is not needed.
