## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-04-14 - Optimize Directory Size Calculation
**Learning:** Path.rglob is significantly slower than manual os.scandir with an iterative stack for calculating directory sizes in large structures.
**Action:** Use os.scandir with a stack and follow_symlinks=False when performance is critical for deep directory traversal.
