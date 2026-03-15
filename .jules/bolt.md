## 2026-01-23 - Lazy Directory Size Evaluation and scandir Optimization
**Learning:** When evaluating directory structures or calculating sizes for large amounts of candidates, eager recursive evaluation (like `Path.rglob`) can be extremely slow. For calculations like recursive directory sizing, using `os.scandir` in a manual loop is significantly faster.
**Action:** When aggregating metadata that is not strictly needed for all entries (e.g., sizes for files that might be ignored/preserved), use lazy evaluation with properties and caching. For efficient traversal, prefer `os.scandir` over `Path.rglob` while carefully handling inner `OSError`s.

## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.