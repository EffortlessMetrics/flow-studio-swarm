## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2025-01-28 - Defer Path instantiation and reduce OS I/O
**Learning:** Instantiating `pathlib.Path` objects and calling `.exists()` inside a loop for directory iterations is a bottleneck. We can reduce I/O by utilizing `os.scandir` to extract strings and sort them natively, deferring existence checks until later.
**Action:** Replace `self.runs_root.iterdir()` loops with `os.scandir`, extracting `entry.name` directly, and perform string operations `os.path.join(runs_root_str, run_name, ...)` instead of `Path` manipulation for high-volume endpoints like `list_runs`.
