## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2024-04-27 - [Avoid copy.deepcopy on heavily nested dataclasses]
**Learning:** Using copy.deepcopy on heavily nested dataclasses (like RunPlanSpec) is a major performance bottleneck.
**Action:** Implement custom clone() methods that manually construct the objects and perform shallow copies on internal collections for ~10x speedups.
