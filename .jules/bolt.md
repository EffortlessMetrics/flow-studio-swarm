## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2026-01-24 - Async I/O for Run Listing
**Learning:** Synchronous file I/O in API routes blocks the event loop, degrading performance for all users. `asyncio.to_thread` is the standard solution for offloading these blocking operations in FastAPI.
**Action:** Wrap blocking I/O calls (like `os.scandir` or `json.load`) in `asyncio.to_thread` when they are called from `async def` route handlers.
