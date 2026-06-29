## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2024-06-29 - Replace deepcopy with dict serialization
**Learning:** In this Python codebase, for complex dataclasses (like RunPlanSpec), using native dict serialization (from_dict(to_dict(x))) is a preferred performance optimization over copy.deepcopy() because it avoids reflection overhead and is significantly faster (~3-4x).
**Action:** Prefer dict serialization over deepcopy when duplicating dataclasses.
