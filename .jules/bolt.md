## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2024-05-18 - Replacing Deepcopy in Nested Dataclasses
**Learning:** In heavily nested dataclasses like `RunPlanSpec` and `NavigatorOutput`, `copy.deepcopy` is very slow. Creating shallow copies of mutable fields inside the dataclass using `dataclasses.replace` is much faster (~4-6x speedup).
**Action:** Always prefer using `dataclasses.replace` over `copy.deepcopy` when copying dataclasses that have nested structures, and explicitly handle mutable fields like lists and sub-dataclasses manually.
