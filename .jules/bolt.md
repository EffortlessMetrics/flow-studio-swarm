## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-03-05 - Fast Recursive Directory Size Calculation
**Learning:** `pathlib.Path.rglob("*")` is highly inefficient for recursively calculating directory size because it creates Path objects for everything and does more overhead. `os.scandir` is much faster.
**Action:** Replace `Path.rglob` with a recursive function using `os.scandir` to calculate directory size.
