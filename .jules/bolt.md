## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2024-03-24 - Lazy Evaluation and Scandir
**Learning:** Using `Path.rglob` and eager size computation during large directory scans is highly inefficient.
**Action:** Replace `rglob` with recursive `os.scandir` for faster filesystem traversal, and use `@property` with a backing cached field for lazy evaluation of expensive metadata like directory size.
