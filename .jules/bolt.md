## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-03-13 - Replace pathlib.Path.rglob with os.scandir for directory size
**Learning:** Calculating directory sizes using `pathlib.Path.rglob` is significantly slower than using a recursive function with `os.scandir` because `os.scandir` caches file attributes (like `is_file`, `is_dir`, `stat`), whereas `rglob` can trigger additional system calls.
**Action:** When calculating recursive directory sizes or iterating through many files where performance is critical, replace `pathlib.Path.rglob` with a recursive function using `with os.scandir(dir_path) as it:`. Ensure `follow_symlinks=False` is used to prevent infinite loops, and place `try...except OSError` blocks *inside* the iteration loop.
