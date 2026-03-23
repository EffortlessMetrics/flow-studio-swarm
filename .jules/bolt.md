## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2026-03-22 - Optimize Recursive Directory Traversal
**Learning:** For recursively traversing directories and calculating sizes across a significant number of files and folders (e.g., getting run directory sizes), `pathlib.Path.rglob` is slow because it creates many `Path` objects and checks unnecessarily. `os.scandir` is 3x+ faster.
**Action:** Use a recursive inner function with `os.scandir` (ensuring we avoid traversing symlinks by passing `follow_symlinks=False` to `is_dir()`) instead of `rglob` when calculating cumulative directory size for performance-critical directory operations.