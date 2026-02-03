## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2026-01-23 - Async File I/O for Run Listing
**Learning:** `RunStateManager.list_runs` performs synchronous file I/O (`os.scandir`, `path.exists`, `read_text`) which blocks the main asyncio event loop in FastAPI, causing significant lag (0.22s for 30k runs).
**Action:** Use `asyncio.to_thread` to offload these blocking operations to a separate thread, reducing event loop lag (to ~0.05s) and improving server responsiveness.
