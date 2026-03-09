## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-03-09 - Lazy Directory Sizing
**Learning:** When listing directory sizes via recursive size computation (e.g., in GC discovery across many thousands of folders), eagerly computing the full size of every folder via `Path.rglob` is significantly slower and highly resource-intensive.
**Action:** Replace `Path.rglob` with an `os.scandir` recursive function to improve metadata caching efficiency. Note: converting dataclass properties requires caution to preserve compatibility with `asdict()` and serialization.
