## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-05-07 - Optimize Chronological Object Sorting
**Learning:** In Python, sorting a large list of objects using a custom `sort_key` that creates tuples and calculates timestamps (e.g. `s.created_at.timestamp()`) incurs a significant overhead. If the object IDs are generated such that their lexicographical order equals chronological order, sorting directly by string ID, followed by a stable sort for secondary categorization, is significantly faster.
**Action:** Prioritize sorting by string ID and utilizing Python's stable sort over computing complex keys and creating tuple structures.
