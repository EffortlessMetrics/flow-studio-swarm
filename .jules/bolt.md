## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2024-05-24 - Faster deep cloning of nested dataclasses
**Learning:** Using `copy.deepcopy` on heavily nested dataclasses (like `RunPlanSpec`) is an anti-pattern in Python that causes severe performance degradation due to heavy memory allocation overhead and recursive object introspection.
**Action:** When a full deep clone is required for nested dataclasses, prefer using JSON dictionary conversion (`run_plan_spec_from_dict(run_plan_spec_to_dict(obj))`), which benchmarking showed to be ~4x faster in our codebase, while maintaining full safety.
