## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2024-06-17 - Optimize Directory Iteration
**Learning:** Path.iterdir() is slow on very large directories because it instantiates Path objects for every item, and checking file existence on each item is an expensive bottleneck.
**Action:** Use os.scandir() and sort by cached metadata (like names), then slice before checking file existence on a subset of items.
