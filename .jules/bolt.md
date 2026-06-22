## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2024-06-22 - Optimize iterate dir loops
**Learning:** `Path.iterdir()` scales poorly with large directories (like runs/) because it instantiates Path objects for every single entry before you can even filter them. `os.scandir()` provides a 20x performance improvement for extracting lightweight string names from large directories.
**Action:** When extracting names or doing simple filtering on large directories, use `os.scandir()` to extract string paths, and only instantiate `Path` objects for the specific entries needed.
