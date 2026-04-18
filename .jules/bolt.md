## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-04-18 - Optimize Directory Size Calculation
**Learning:** When calculating the size of large directory structures recursively, `Path.rglob("*")` incurs significant overhead. Using an iterative stack with `os.scandir` and cached stat calls is substantially faster.
**Action:** When optimizing operations on large directories, avoid calling `os.path.exists` or other expensive checks on every item. Instead, sort candidates by cached metadata (such as mtime from `os.scandir`) first, and only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned. Use `os.scandir` iteratively instead of `Path.rglob` for performance-critical path traversals.
