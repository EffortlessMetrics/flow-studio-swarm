## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2026-01-24 - Async Wrapper for Blocking I/O
**Learning:** Even optimized file I/O operations (like `os.scandir` with deferred checks) block the event loop in `async def` FastAPI routes, causing the entire server to stall during large directory listings.
**Action:** Always wrap blocking I/O operations (like `list_runs`) in `asyncio.to_thread` when exposing them via async API endpoints to ensure the event loop remains responsive.
