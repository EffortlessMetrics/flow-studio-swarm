## 2026-01-24 - Faster Recursive Directory Traversal
**Learning:** Computing recursive directory sizes using `pathlib.Path.rglob("*")` is extremely slow in large file hierarchies compared to manually walking the tree with `os.scandir()`. `rglob` constructs expensive `Path` objects for every element. Also, eager calculation of directory sizes during object initialization drastically degrades startup performance when the sizes are not universally accessed.
**Action:** Use a recursive function traversing `os.scandir` for computing sizes, and calculate it lazily via a `@property` instead of eagerly on object creation. Ensure `follow_symlinks=False` is passed to `is_dir()` to prevent infinite loops, and gracefully catch `OSError`.

## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.