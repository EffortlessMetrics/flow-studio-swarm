## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-04-15 - Optimize get_dir_size with os.scandir
**Learning:** Using `Path.rglob("*")` is significantly slower than using `os.scandir` iteratively due to the overhead of recursive yielding and Path object instantiation, which is especially noticeable when calculating the sizes of many large directories during runs_gc.
**Action:** Replaced `Path.rglob("*")` with an iterative `os.scandir` implementation using a stack, an inner try...except block, and `follow_symlinks=False` to avoid recursion limits, handle unreadable files safely, and correctly measure symlinks.
