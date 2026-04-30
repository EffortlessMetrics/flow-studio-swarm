## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2024-05-18 - Avoid copy.deepcopy on heavily nested dataclasses
**Learning:** Using copy.deepcopy on deeply nested Pydantic models/dataclasses like RunPlanSpec is a significant performance bottleneck in this codebase, being ~3.5x slower than dictionary serialization.
**Action:** For safe and significant speedups, use JSON dictionary conversion (e.g., run_plan_spec_from_dict(run_plan_spec_to_dict(obj))) when a full deep clone is explicitly required.
