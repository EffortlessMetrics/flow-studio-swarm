## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-01-24 - Efficient Recursive Directory Sizing
**Learning:** `Path.rglob` is significantly slower than using `os.scandir` recursively for calculating directory sizes because `rglob` instantiates `Path` objects for every file.
**Action:** When calculating recursive directory sizes efficiently, replace `pathlib.Path.rglob` with a recursive function using `with os.scandir(dir_path) as it:`. To ensure accuracy, place `try...except OSError` blocks *inside* the iteration loop around individual `stat()` and `is_dir()` calls rather than wrapping the entire loop. Use `follow_symlinks=False` for `is_dir()`, `is_file()`, and `stat()` to prevent infinite loops, double-counting, or aborting the entire directory traversal on broken symlinks.
