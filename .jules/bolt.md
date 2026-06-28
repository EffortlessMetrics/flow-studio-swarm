## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2024-06-28 - Native Dict Serialization over deepcopy
**Learning:** Using native dict serialization (`from_dict(to_dict(x))`) is significantly faster (~3-4x) than `copy.deepcopy()` for complex dataclasses like `RunPlanSpec`. This avoids the substantial reflection overhead associated with `deepcopy()`.
**Action:** Always prefer native serialization methods over `copy.deepcopy()` for cloning complex configuration objects in critical performance paths.
