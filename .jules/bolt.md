## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2024-03-20 - rglob vs scandir for directory sizing
**Learning:** `os.scandir` is significantly faster than `pathlib.Path.rglob` for recursively calculating directory size because it avoids creating intermediate `Path` objects.
**Action:** Use `os.scandir` with recursion for directory size calculations, remembering to set `follow_symlinks=False` on `is_dir()` to prevent infinite loops.