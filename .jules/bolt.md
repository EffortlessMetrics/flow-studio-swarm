## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-04-13 - Optimize get_dir_size with os.scandir
**Learning:** Using pathlib's rglob for calculating directory sizes recursively can be slow due to the overhead of creating Path objects for every file.
**Action:** Replaced rglob with an iterative os.scandir implementation to avoid the Path overhead and speed up the total dir size calculation.
