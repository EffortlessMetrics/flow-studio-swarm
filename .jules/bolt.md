## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2026-01-23 - Recursive Directory Size Optimization
**Learning:** Calculating total directory sizes recursively using `pathlib.Path.rglob` has significant overhead for deeply nested or large directories compared to native directory iteration.
**Action:** Replace `pathlib.Path.rglob` with recursive `os.scandir` for computing sizes of large directory trees. Ensure `follow_symlinks=False` is passed to `is_dir()` to avoid infinite loops across cyclic symlinks, but preserve symlink target behavior by omitting it from `is_file()` or `stat()`.