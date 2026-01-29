## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2026-01-23 - Cache Lookup in Run Listing
**Learning:** Even with deferred file existence checks, `RunStateManager.list_runs` was still reading and parsing `run_state.json` from disk for every candidate run, causing a bottleneck when listing many runs.
**Action:** Implemented a cache lookup in `list_runs` to use the in-memory `_cache` if available, reducing `Path.read_text` calls to zero for cached runs.
