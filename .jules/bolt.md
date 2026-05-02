## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2024-05-02 - Replace deepcopy with serialization/dataclasses.replace
**Learning:** `copy.deepcopy` is extremely slow on heavily nested dataclasses like `RunPlanSpec` and `NavigatorOutput`, causing significant performance bottlenecks during clone and mutation operations.
**Action:** Use `json.loads(json.dumps())` or custom serialization/deserialization methods (e.g., `run_plan_spec_from_dict(run_plan_spec_to_dict())`) for deep cloning, or use `dataclasses.replace` to selectively update fields and share references, providing ~3x to ~8x speedups over `copy.deepcopy`.
