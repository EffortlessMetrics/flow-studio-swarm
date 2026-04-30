## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2024-05-18 - Deferring File Checks with list_all_run_ids
**Learning:** Checking `os.path.exists` on every run directory in a `runs/` folder with 50k+ items was scaling O(N) during `list_runs_paginated`.
**Action:** Introduced `list_all_run_ids` to fetch O(N) directory names without file existence checks, and sliced it to only invoke O(1) checks during pagination.
