## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2024-05-24 - Defer File Existence Checks in `SpecManager.list_runs`
**Learning:** When listing items from a large directory, checking file existence (`os.path.exists`) and instantiating `Path` objects for every item is a significant bottleneck.
**Action:** Sort candidates by extracting lightweight names directly from `os.scandir()`, then only perform expensive operations (`exists()`, `is_dir()`) on the entries actually processed, deferring unnecessary file I/O overhead.
