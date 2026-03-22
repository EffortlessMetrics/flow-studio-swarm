## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-01-23 - scandir vs rglob for Directory Traversal
**Learning:** When calculating the total size of large, deeply nested directories (like runs in this repository), using pathlib.Path.rglob() incurs significant overhead compared to explicitly recursing with os.scandir().
**Action:** Always prefer os.scandir() (with follow_symlinks=False for directories) over rglob() when traversing large directories for file metadata like sizes.
