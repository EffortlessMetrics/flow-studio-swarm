## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2025-02-23 - Dataclass deepcopy optimization in Run Plan API
**Learning:** In this codebase, copying complex dataclasses like `RunPlanSpec` using `copy.deepcopy()` is slow due to reflection overhead. Using native dict serialization via `run_plan_spec_from_dict(run_plan_spec_to_dict(x))` is ~4x faster.
**Action:** Prefer `from_dict(to_dict(x))` over `copy.deepcopy()` for large dataclass structures where performance is critical.
