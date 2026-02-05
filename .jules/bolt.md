## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-01-24 - Async Function != Non-Blocking
**Learning:** `RunStateManager` in `swarm/api/services/run_state.py` defines `async` methods like `create_run` and `update_run`, but they perform synchronous file I/O (e.g., `write_text`, `os.replace`), blocking the event loop. This is a deceptive anti-pattern.
**Action:** When optimizing async code, verify that `async` functions don't just "await" nothing or only other synchronous code. Use `asyncio.to_thread` for blocking I/O.
