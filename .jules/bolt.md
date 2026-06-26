## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2024-05-24 - Optimize iterdir() with os.scandir() for large directories
**Learning:** In large directories (like runs output), `pathlib.Path.iterdir()` can become a performance bottleneck because it instantiates `Path` objects for every entry before sorting. Extracting lightweight string names with `os.scandir()` within a context manager and sorting those strings improves performance considerably (e.g. ~10-15x faster for 10k directories).
**Action:** Use `os.scandir()` over `iterdir()` when iterating and sorting large directories.
