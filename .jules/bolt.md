## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2026-01-24 - Async Wrapper for Sync I/O
**Learning:** Calling synchronous methods that perform file I/O (like `RunStateManager.list_runs`) directly in `async` route handlers blocks the event loop, degrading performance under concurrency.
**Action:** Wrap such synchronous calls using `asyncio.to_thread` (e.g. `list_runs_async`) to offload execution to a thread pool and keep the main loop responsive.
