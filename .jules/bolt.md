## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-01-24 - Faster Recursive Directory Size
**Learning:** `pathlib.Path.rglob` is significantly slower than traversing directories with `os.scandir()` for large hierarchies (e.g. counting total sizes of `runs/` or `examples/`). `os.scandir` avoids caching full Path objects and extra system calls.
**Action:** When calculating recursive directory sizes recursively, use a custom recursive function looping over `os.scandir()`. Ensure `try...except OSError` block is kept close to `stat()` to catch permission errors, use `is_file()` and `stat()` without `follow_symlinks=False` to preserve accurate calculation over symlinks, and importantly, use `entry.is_dir(follow_symlinks=False)` to avoid infinite loops from symlinked directories.
