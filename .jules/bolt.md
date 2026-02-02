## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2026-01-23 - Unblocking Event Loop with asyncio.to_thread
**Learning:** Synchronous file I/O operations (like `os.scandir` or `pathlib.Path.read_text`) in `RunStateManager.list_runs` block the main event loop when called from asynchronous FastAPI routes, degrading concurrency.
**Action:** Wrap blocking I/O methods in `asyncio.to_thread` (introduced in Python 3.9) to offload execution to a separate thread, keeping the event loop responsive.
