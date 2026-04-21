## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-04-21 - rglob Bottleneck
**Learning:** Path.rglob() creates significant overhead for pure file enumeration compared to os.scandir() because Path objects are instantiated for every entry regardless of whether they are needed, which balloons memory and processing time for large directories.
**Action:** Use an iterative os.scandir() approach when recursively walking large directory trees instead of Path.rglob() to avoid unnecessary object creation.
