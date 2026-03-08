## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2024-05-20 - Faster Directory Size Calculation
**Learning:** Using `pathlib.Path.rglob("*")` inside `get_dir_size` is slow for directories with many files because it creates generator overhead and performs redundant internal `stat` checks.
**Action:** Replace `rglob` with recursive `os.scandir` to avoid generator overhead and reduce redundant `stat` calls.
