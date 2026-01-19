## 2025-01-20 - Deepcopy vs JSON Load
**Learning:** `copy.deepcopy()` can be significantly slower (~0.19ms) than `json.load()` (~0.11ms) for small JSON files (~7KB).
**Action:** When caching mutable data structures, consider returning the cached object reference with a warning/contract of immutability instead of deep-copying, if performance is critical and the data is treated as read-only.
