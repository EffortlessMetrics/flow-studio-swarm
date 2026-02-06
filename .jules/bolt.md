## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2026-01-23 - Async I/O Offloading
**Learning:** Synchronous file I/O operations (like `path.read_text()` or `os.scandir()`) inside `async` methods block the entire asyncio event loop, severely limiting concurrency in FastAPI applications.
**Action:** Wrap all blocking I/O calls in `await asyncio.to_thread(...)` to offload them to a thread pool, allowing the event loop to continue processing other requests.
