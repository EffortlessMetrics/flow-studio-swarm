## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2026-01-24 - Deepcopy on Dataclasses
**Learning:** `copy.deepcopy` is extremely slow when used on deeply nested dataclasses like `RunPlanSpec` (~10x slower).
**Action:** Implement and use custom `.clone()` methods that perform manual object construction and shallow copies of internal collections instead of relying on the generic `copy.deepcopy` utility.
