## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-01-24 - `os.scandir` is significantly faster than `Path.rglob`
**Learning:** In Python, `os.scandir` avoids creating heavy `Path` objects and caches file attributes (like `.is_file()`), leading to >2.5x speedup for directory size calculations compared to `Path.rglob("*")`.
**Action:** When optimizing directory traversal by replacing `Path.rglob("*")` with a custom `os.scandir` implementation, use an iterative stack approach rather than recursion. Ensure the `try...except OSError` block explicitly wraps the individual file operations inside the `for entry in it:` loop, and explicitly use `follow_symlinks=False` for checks and stat calls to prevent infinite symlink loops.
