## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2026-01-23 - Offloading Blocking I/O in FastAPI
**Learning:** Calling synchronous blocking methods (like `os.scandir` and file reads in `RunStateManager.list_runs`) from `async def` endpoints in FastAPI blocks the main event loop, significantly degrading concurrency (e.g., blocking heartbeats for ~250ms with 20k runs).
**Action:** Wrap blocking calls in `await asyncio.to_thread(...)` to offload them to a separate thread, keeping the event loop responsive.
