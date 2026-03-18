## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2026-03-18 - Recursive Directory Size & Lazy Evaluation
**Learning:** `pathlib.Path.rglob("*")` is slow for traversing directories and aggregating sizes. Also, eagerly evaluating size (or other metadata) for thousands of directory items blocks the main thread when many items won't even be displayed or used.
**Action:** Use `os.scandir()` recursively (with `follow_symlinks=False` on `is_dir()`) instead of `rglob` to aggregate size. For metadata that isn't always needed, implement lazy evaluation (e.g. a `@property` with a backing cached field) instead of eagerly calculating it during object initialization.