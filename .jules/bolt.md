## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2026-01-23 - Async Route Blocking
**Learning:** FastAPI async routes run on the main event loop. Synchronous I/O operations (like `os.scandir` in `list_runs`) block the entire server.
**Action:** Always wrap synchronous I/O calls in `await asyncio.to_thread(...)` within async routes to maintain responsiveness.
