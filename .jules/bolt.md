## 2024-05-23 - Search Complexity Bottleneck
**Learning:** The search function was performing O(N*M) nested loop lookups for agents, scanning all flows repeatedly. This scales poorly as flow count increases. Additionally, `load_artifact_catalog` was reading/parsing JSON on every graph load, causing IO overhead.
**Action:** Use inverted indexes (e.g. `agent -> [flows]`) pre-computed at load time for O(1) lookups. Implement mtime-based caching for frequent file reads.
