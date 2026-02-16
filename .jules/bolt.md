## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2024-10-26 - [Backend Performance] Batch Ingestion Transaction
**Learning:** DuckDB auto-commits by default, and `StatsDB._transaction()` only provides thread safety via locks, not SQL transactions. Wrapping batch operations in an explicit `BEGIN TRANSACTION` / `COMMIT` block significantly improves performance (observed ~1.8x speedup for 5000 events).
**Action:** Always wrap bulk database operations in explicit SQL transactions when using DuckDB via `StatsDB`.
