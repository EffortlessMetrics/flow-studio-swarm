## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-03-11 - Use `os.scandir` for Recursive Directory Sizing
**Learning:** `Path.rglob("*")` is very slow for calculating recursive directory sizes because it involves path resolution and creates a complete list (or iterator) of all objects before checking if they are files.
**Action:** Use a recursive function with `with os.scandir(dir_path) as it:` instead. Place `try...except OSError` blocks *inside* the iteration loop (around individual `stat()` and `is_dir()` calls) rather than wrapping the entire loop. Use `follow_symlinks=False` for `is_dir()`, `is_file()`, and `stat()` to prevent infinite loops, double-counting, or aborting the entire directory traversal on broken symlinks.
