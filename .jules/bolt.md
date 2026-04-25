## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2025-02-21 - Replace deepcopy with clone
**Learning:** The Python copy.deepcopy() function is a major performance bottleneck for deeply nested dataclasses like RunPlanSpec. Using custom clone methods speeds up the operation by ~7x.
**Action:** When cloning objects, especially nested ones, implement custom clone() methods instead of relying on copy.deepcopy() to avoid performance overhead.
