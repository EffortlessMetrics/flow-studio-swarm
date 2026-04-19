## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-04-19 - Path.rglob("*") Traversal Overhead
**Learning:** Using `Path.rglob("*")` for full recursive directory traversal is significantly slower than using an explicit `os.scandir` stack, as `rglob` builds massive object graphs and performs heavy abstraction layering over simple OS calls.
**Action:** When calculating directory sizes or deeply traversing large file trees, always use a custom `os.scandir` stack implementation rather than `Path.rglob` to minimize overhead.
