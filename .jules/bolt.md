## 2025-01-20 - JSON Caching Optimization
**Learning:** `json.load()` is fast (~0.1ms for 8KB) but `copy.deepcopy()` is slower (~0.2ms). To optimize frequent JSON reads, cache the loaded object and return it by reference (read-only), avoiding `deepcopy`.
**Action:** When caching JSON config/artifacts, document that the returned object is read-only and avoid defensive copying if performance is critical.
