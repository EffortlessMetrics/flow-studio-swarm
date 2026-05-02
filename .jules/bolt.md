## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-02-14 - Faster RunPlanSpec Deep Copy
**Learning:** Using `copy.deepcopy` on heavily nested dataclasses (e.g., `RunPlanSpec`) is a known performance anti-pattern and can be slow.
**Action:** When a full deep clone is required, use JSON dictionary conversion (`run_plan_spec_from_dict(run_plan_spec_to_dict(obj))`) instead.
