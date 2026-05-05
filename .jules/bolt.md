## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-05-05 - Streaming Filtered Pagination
**Learning:** Slicing raw unfiltered collections breaks pagination offsets, but resolving filtering by loading and sorting all objects into memory just to return a small slice is an inefficient memory anti-pattern. We can iterate through the unfiltered IDs, evaluate the condition dynamically, track skipped offsets and limits, and accumulate matches without allocating large lists.
**Action:** Always optimize paginated lists by combining offset skipping and limit tracking directly into the filter evaluation loop instead of delegating to full-fetch bulk list methods.
