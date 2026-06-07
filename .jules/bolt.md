## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-01-23 - Optimize Directory Traversals with Lexicographical Sorting
**Learning:** When using `os.scandir()` to optimize `Path.iterdir()` for large directories, avoid calling `.stat()` or instantiating `Path` objects inside the loop. If the filenames (like run IDs) are generated chronologically by string representation, simply collecting `entry.name` and sorting the list of strings is sufficient and avoids severe performance bottlenecks caused by synchronous system calls.
**Action:** In Python directory traversals where IDs encode time, use `os.scandir()` to collect string names, sort them natively, and only convert the top N required entries back into `Path` objects and perform filesystem checks on them.
