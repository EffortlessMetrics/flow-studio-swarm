## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-04-24 - Avoid deepcopy on nested dataclasses
**Learning:** A known Python performance anti-pattern in this codebase is using `copy.deepcopy` on heavily nested dataclasses (e.g., plan specs like `RunPlanSpec`). For significant speedups (~10x), implement and use custom `clone()` methods that manually construct the objects and perform shallow copies on their internal collections.
**Action:** When copying nested dataclasses, especially those containing lists or other dataclasses, implement explicit `clone()` methods rather than relying on `copy.deepcopy`.
