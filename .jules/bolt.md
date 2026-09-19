## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-01-23 - Lexical vs st_mtime Sorting
**Learning:** When listing items from a large directory where directory names embed timestamps (e.g., `flow_id-YYYYMMDDHHMMSS`), sorting entries lexically by name is significantly faster than sorting by `st_mtime` from `os.scandir`.
**Action:** Use simple string comparisons for sorting directory lists when names contain timestamps instead of accessing file properties to reduce overhead.
