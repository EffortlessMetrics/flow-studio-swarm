## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-04-19 - Defer Path objects in large directories
**Learning:** When scanning large directories recursively to get total sizes, using `Path.rglob` can be extremely slow because it creates a `Path` object for every file, creating significant overhead.
**Action:** Use `os.scandir` directly with an iterative stack approach without resolving full paths or stat unless necessary.
