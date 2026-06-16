## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.## 2026-01-23 - Use os.scandir to avoid Path instantiation overhead
**Learning:** When listing items from a large directory in list_runs and sorting them, instantiating Path objects for every entry via Path.iterdir() and checking is_dir() creates unnecessary overhead. Using os.scandir() allows filtering and sorting entries by caching attributes natively before creating Path objects for only the limited set that will be processed.
**Action:** Replaced Path.iterdir() with os.scandir() in swarm/api/services/spec_manager.py to improve performance when loading run histories.

## 2026-01-23 - Use os.scandir to avoid Path instantiation overhead
**Learning:** When listing items from a large directory in list_runs and sorting them, instantiating Path objects for every entry via Path.iterdir() and checking is_dir() creates unnecessary overhead. Using os.scandir() allows filtering and sorting entries by caching attributes natively before creating Path objects for only the limited set that will be processed.
**Action:** Replaced Path.iterdir() with os.scandir() in swarm/api/services/spec_manager.py to improve performance when loading run histories.
