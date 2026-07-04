## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-01-23 - Optimize list_runs with scandir in SpecManager
**Learning:** Just like RunStateManager, SpecManager.list_runs() can become a bottleneck when traversing large directories using iterdir() combined with file existence checks for every run. However, using scandir() and sorting by st_mtime causes a performance regression on POSIX systems because st_mtime forces a stat() system call for every entry. Instead, we can sort by lexical directory name, since runs are already naturally ordered (run_2, run_1).
**Action:** Use os.scandir to fetch directory names, sort lexically (which is O(1) regarding system calls), and only check run_state.json existence for the top N requested results.
