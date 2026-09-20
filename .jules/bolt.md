## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-09-20 - Avoid st_mtime in directory traversals
**Learning:** Using `entry.stat().st_mtime` to sort results from `os.scandir()` on POSIX systems is an anti-pattern when directory names contain chronological information (like timestamps). The `.stat()` call forces an O(N) system call for every directory entry, causing severe performance degradation for large histories.
**Action:** Always use lexical sorting on chronologically-named paths directly instead of fetching metadata. The difference drops execution time from O(N) I/O bounds to O(1) in stat calls.
