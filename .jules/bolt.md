## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2026-03-16 - Faster recursive directory size calculation
**Learning:** `pathlib.Path.rglob("*")` is a significant performance bottleneck for operations that need to scan large, deep directory structures to calculate sizes. This is because `rglob()` is relatively slow, and subsequent `is_file()` or `stat()` calls trigger additional system calls. Replacing `rglob` with `os.scandir()` in a recursive implementation utilizes cached directory entry properties, resulting in faster size aggregations.
**Action:** When calculating total sizes for recursive directories, prefer `os.scandir()` over `pathlib.Path.rglob()`, ensuring `entry.is_dir(follow_symlinks=False)` is used to prevent infinite recursion on symlinks.