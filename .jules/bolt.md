## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-03-13 - Optimize Recursive Directory Sizing with os.scandir
**Learning:** `pathlib.Path.rglob("*")` is slow for calculating directory sizes because it yields `Path` objects that require a separate `stat()` system call to get file size (`st_size`).
**Action:** Use a recursive function with `os.scandir` instead. `os.scandir` caches file attributes (like `st_size` and `is_dir`) during directory iteration, eliminating the need for separate `stat()` calls and providing a ~3x speedup. Ensure to use `follow_symlinks=False` for `is_dir()` to prevent infinite loops, but NOT for `is_file()` or `stat()` to match original `Path.stat()` symlink behavior.
