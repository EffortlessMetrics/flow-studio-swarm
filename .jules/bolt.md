## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2024-10-23 - os.scandir Over pathlib.iterdir
**Learning:** pathlib.Path.iterdir() instantiates Path objects for every directory entry, creating a massive overhead on directories with 50k+ items.
**Action:** Use os.scandir() inside a context manager to extract simple string attributes and only instantiate Path objects when genuinely needed.
