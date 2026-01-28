## 2025-01-01 - [Run Listing Optimization]
**Learning:** `heapq.merge` with `itertools.islice` is a powerful pattern for paginating merged sorted streams without materializing the full list. This reduced the time complexity of pagination from O(N log N) to O(limit) for list generation.
**Action:** When merging multiple sorted sources (e.g. active vs legacy vs examples), prefer lazy merging over concatenation + sort, especially when only a slice is needed.
