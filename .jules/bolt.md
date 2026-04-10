## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2025-03-02 - Path.rglob Performance Overhead
**Learning:** Instantiating `Path` objects via `Path.rglob("*")` inside a large directory traversal is expensive. Using `os.scandir` iteratively and reusing cached stats instead of calling `.stat()` on `Path` objects is significantly faster (around ~58% improvement observed).
**Action:** For performance-critical directory traversals, avoid `Path.rglob` and favor a custom iterative stack with `os.scandir`, ensuring exception handling for `OSError` and using `follow_symlinks=False` to handle symlinks correctly.
