## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-06-06 - Optimize Directory Traversal for Path Objects
**Learning:** Using `Path.iterdir()` chained with `p.is_dir()` on large scale directories in Python creates a severe performance bottleneck because it instantiates a `Path` object for every entry and forces an expensive synchronous `stat` system call.
**Action:** Use `os.scandir()` to efficiently extract string names and cached OS metadata (like `entry.is_dir()`) first, sort the strings, and then construct the resulting `Path` objects, preventing the N+1 `stat` syscall issue.
