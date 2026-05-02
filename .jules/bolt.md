## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2024-05-24 - Replace copy.deepcopy with Dictionary Serialization
**Learning:** `copy.deepcopy` on heavily nested dataclasses (like `RunPlanSpec` or `NavigatorOutput`) is a known Python performance anti-pattern.
**Action:** Use dictionary serialization (e.g., `navigator_output_from_dict(navigator_output_to_dict(obj))`) when a full deep clone is required for a ~3x speedup.
