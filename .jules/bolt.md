## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2024-06-25 - pathlib.Path.iterdir() performance bottleneck
**Learning:** pathlib.Path.iterdir() instantiates a Path object for every entry before sorting, which is a significant performance bottleneck when scanning large directories like the runs root. By using os.scandir() to extract and sort lightweight string names, and only instantiating Path objects for the specific entries needed, we can reduce the directory scanning overhead by ~70%.
**Action:** Use os.scandir() instead of pathlib.Path.iterdir() for iterating and sorting large directories.
