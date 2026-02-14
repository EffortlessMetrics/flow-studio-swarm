## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2026-02-06 - Batch Ingestion in DuckDB
**Learning:** Inserting thousands of rows individually into DuckDB (even in-memory) is significantly slower (by ~3.5x) than batch insertion, due to transaction overhead and Python-to-C context switching.
**Action:** Use `executemany` with a temporary staging table for bulk data ingestion, then use `INSERT ... SELECT ... RETURNING` to efficiently merge and retrieve IDs of new rows for further processing.
