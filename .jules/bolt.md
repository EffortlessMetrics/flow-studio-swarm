## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2024-10-24 - Replace deepcopy on heavily nested dataclasses
**Learning:** Using `copy.deepcopy` on heavily nested Python dataclasses (like `RunPlanSpec` or `NavigatorOutput`) is a significant performance anti-pattern in this codebase. Attempting to manually copy all nested mutable fields using `dataclasses.replace()` can be brittle and crash-prone.
**Action:** For safe and significant speedups on deep nesting, use JSON dictionary conversion (`from_dict(to_dict(obj))`) when a full deep clone is required (~3x speedup). When only a few specific paths are mutated, safely use `dataclasses.replace()` on only the exact path being updated (~5x speedup).
