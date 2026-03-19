## 2026-01-24 - Faster Directory Sizing with os.scandir
**Learning:** `Path.rglob("*")` is slow for recursively calculating directory sizes because it creates many intermediate `Path` objects. A stack-based manual loop using `os.scandir` is significantly faster.
**Action:** When repeatedly calculating directory sizes (like in GC scripts traversing thousands of run directories), use `os.scandir` in a manual loop, being careful to pass `follow_symlinks=False` to `is_dir()` to avoid infinite loops.

## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.