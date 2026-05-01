## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-05-01 - Avoid copy.deepcopy on heavily nested dataclasses
**Learning:** Using `copy.deepcopy` on heavily nested dataclasses (like `NavigatorOutput`) is extremely slow and a performance anti-pattern in Python.
**Action:** Instead of `deepcopy`, use `dataclasses.replace` targeting only the specific nested fields being mutated. This avoids the massive overhead of full deep copies and shares references for untouched paths, resulting in a ~10x speedup.
