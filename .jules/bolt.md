## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-05-13 - Optimize directory traversal with os.scandir
**Learning:** Using `pathlib.Path.iterdir()` combined with `.is_dir()` and `.name` on large directories is inefficient because it instantiates `Path` objects and forces synchronous system stat calls for every item. `os.scandir()` provides efficient access to cached OS metadata.
**Action:** Use `os.scandir()` instead of `.iterdir()` for listing runs and checking directory properties, and explicitly wrap `entry.path` with `Path()` only when downstream code strictly requires a `Path` object.
