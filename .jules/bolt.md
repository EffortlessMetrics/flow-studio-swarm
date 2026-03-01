## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2025-01-26 - Optimized list_runs by validating cache with st_mtime
**Learning:** When dealing with frequent reads of JSON files on disk (like `run_state.json` in `RunStateManager.list_runs`), relying solely on in-memory dictionary caching might still lead to redundant I/O parsing if not implemented correctly. However, caching the `os.stat().st_mtime` along with the parsed JSON state allows you to validate if the file has changed on disk before paying the cost of `json.loads`.
**Action:** When implementing file-backed caching, especially for list operations that touch many files, store `(mtime, parsed_data)` in the cache and validate against the current `st_mtime` to skip redundant parsing.
