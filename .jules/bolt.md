## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-01-23 - Optimize directory traversal with os.scandir
**Learning:** pathlib.Path.iterdir() instantiates Path objects and often requires additional explicit stat calls (like .is_dir()). For large directories (like run histories), this is a significant bottleneck.
**Action:** Use os.scandir() which yields lightweight DirEntry objects that cache stat attributes, greatly speeding up operations that filter by directory/file type.
