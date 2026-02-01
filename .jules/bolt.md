## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2026-02-14 - Async I/O vs Caching
**Learning:** Attempting to optimize `list_runs` by caching loaded JSON states introduced a critical stale data regression because run states change frequently (e.g. status updates) and simple caching misses external updates.
**Action:** Prioritize `asyncio.to_thread` to unblock the event loop for I/O operations over risky caching strategies. Speed without correctness is useless.
