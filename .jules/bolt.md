## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2026-02-18 - Offload Synchronous I/O in Async Routes
**Learning:** Even optimized synchronous file operations (like `os.scandir` + sorting) block the asyncio event loop in FastAPI applications. For 5000 items, this caused a ~250ms freeze.
**Action:** Always wrap synchronous file system operations (even "fast" ones) in `await asyncio.to_thread(...)` within async route handlers to maintain responsiveness.
