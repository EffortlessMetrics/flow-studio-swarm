## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-04-22 - [Optimizing Directory Traversal]
**Learning:** `Path.rglob("*")` creates significant overhead when traversing large directory structures because it instantiates a `Path` object for every file and directory. In this codebase, for operations like calculating directory size, this becomes a performance bottleneck.
**Action:** Replace `Path.rglob("*")` with an iterative stack-based `os.scandir` implementation using `follow_symlinks=False` to avoid infinite loops and avoid the overhead of `Path` objects.
