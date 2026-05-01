## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2024-05-24 - Avoid copy.deepcopy on heavily nested objects
**Learning:** Using `copy.deepcopy` on heavily nested dataclasses (like `NavigatorOutput` and `RunPlanSpec`) is a significant performance bottleneck.
**Action:** For safe and significant speedups, use `dataclasses.replace()` to only update the exact path being mutated (allowing the rest of the object to safely share references), or use JSON/dictionary conversion (e.g., `run_plan_spec_from_dict(run_plan_spec_to_dict(obj))`) when a full deep clone is explicitly required.
