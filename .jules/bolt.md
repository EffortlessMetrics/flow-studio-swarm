## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-01-24 - Faster Directory Scanning
**Learning:** Using `pathlib.Path.iterdir()` constructs `Path` objects for every item, which is computationally expensive for large directories. `os.scandir()` yields `DirEntry` objects, returning cached attributes directly without constructing heavy `Path` instances until needed, providing nearly a 4x performance boost.
**Action:** Always prefer `os.scandir()` with a `with` statement for efficient iteration over large directories, and access basic checks like `.is_dir()` on the `DirEntry` object directly.
