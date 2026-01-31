## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2026-01-23 - Async File I/O in Routes
**Learning:** Even fast file operations (like `os.scandir` or `json.loads`) can block the asyncio event loop when dealing with thousands of files, causing latency spikes and timeouts in concurrent requests.
**Action:** Always wrap synchronous file I/O intensive operations in `await asyncio.to_thread(...)` when calling them from an `async` FastAPI route handler.
