## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-01-24 - Avoid Deepcopy on Dataclasses
**Learning:** Using `copy.deepcopy` on heavily nested dataclasses (like `RunPlanSpec`) is a significant performance bottleneck.
**Action:** Use JSON dictionary conversion (e.g., `run_plan_spec_from_dict(run_plan_spec_to_dict(obj))`) when a full deep clone is required for these complex structures to achieve a ~4x speedup.
