## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-02-27 - Lexical Sort for Run Directories
**Learning:** When listing run directories containing timestamp-based IDs (like `run-YYYYMMDD-HHMMSS-xxxxxx`), sorting by `st_mtime` from `os.scandir` is unnecessarily slow because each tuple allocation and `st_mtime` extraction is slower than sorting native strings, and lexical sort perfectly matches descending mtime sort.
**Action:** Use lexical sorting on `entry.name` directly instead of tuple extraction with `entry.stat().st_mtime` when directory formats guarantee timestamp ordering, to achieve ~5x speedups.
