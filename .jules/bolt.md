## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-04-17 - Optimize Directory Traversal
**Learning:** `Path.rglob("*")` is significantly slower than an iterative `os.scandir` stack for large directory traversals, creating a bottleneck when calculating sizes across many directories.
**Action:** Replace `Path.rglob("*")` with a custom `os.scandir` stack implementation using `follow_symlinks=False` and inner `try...except OSError` blocks to safely handle permissions and prevent symlink loops.
