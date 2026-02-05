## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-01-24 - Async Wrapper for Sync I/O
**Learning:** Even with optimized synchronous file I/O (like `os.scandir`), calling it directly in an `async def` route blocks the event loop.
**Action:** Wrap synchronous I/O methods in `asyncio.to_thread` (e.g., `list_runs_async`) when they are called from async API endpoints to ensure the server remains responsive.
