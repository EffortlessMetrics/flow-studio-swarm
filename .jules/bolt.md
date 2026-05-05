## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-05-05 - Avoid Slicing Unfiltered Lists for Paginated Filters
**Learning:** When optimizing paginated list endpoints that filter results, slicing the raw unfiltered list before filtering breaks pagination offsets when items are discarded. Additionally, avoiding full list traversals on heavy data objects saves computation time.
**Action:** Iterate through the unfiltered list, evaluate the filter condition, track a `skipped` counter against the `offset`, and append to the results list until its length reaches the `limit`.
