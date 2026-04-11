## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.## 2026-04-11 - Prevent Path Object Creation for Large Directory Scans
**Learning:** Creating `Path` objects for every file using `Path.rglob("*")` is a major performance bottleneck for large directories (e.g. 50k runs) and can hit recursion limits.
**Action:** Use an iterative `os.scandir` approach with string paths and a stack to traverse large directory trees efficiently.
