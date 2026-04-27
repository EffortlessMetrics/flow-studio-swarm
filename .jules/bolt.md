## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2024-04-27 - Optimize RunPlanSpec deepcopy
**Learning:** `copy.deepcopy` is extremely slow (~10x slower) for heavily nested dataclasses like `RunPlanSpec` due to its internal memoization and generic traversal. Manually reconstructing the objects and performing shallow copies of lists avoids this overhead.
**Action:** Use custom `clone()` methods for critical, frequently copied nested dataclasses instead of `copy.deepcopy`.
