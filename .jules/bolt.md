## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2026-02-12 - DuckDB Batch Ingestion Transaction
**Learning:** Wrapping batch ingestion (`ingest_events`) in a single SQL transaction (`BEGIN TRANSACTION` ... `COMMIT`) reduces auto-commit overhead, improving performance by ~40% for batches of ~2000 events.
**Action:** Always wrap batch database operations in an explicit transaction to minimize transaction overhead.
