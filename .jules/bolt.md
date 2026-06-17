## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-06-17 - Optimize Directory Listing
**Learning:** Path.iterdir() is slow for directories with many files because it creates many Path objects. Sorting the objects is expensive. os.scandir() is significantly faster, and we can sort string file names directly.
**Action:** Use os.scandir() with context managers instead of Path.iterdir() for iterating large directories where performance matters.
