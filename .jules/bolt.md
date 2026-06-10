## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-06-10 - Optimize Directory Iteration
**Learning:** Python's pathlib.Path.iterdir() is noticeably slower when processing thousands of files/directories compared to os.scandir() due to the overhead of instantiating Path objects for every single entry.
**Action:** Prefer os.scandir() over pathlib.Path.iterdir() in performance-critical sections iterating over very large directories, especially when just checking types (.is_dir()) or file names.
