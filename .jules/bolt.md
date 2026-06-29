## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2024-05-18 - Optimized clone deepcopy for complex dataclasses
**Learning:** In this Python codebase, for complex dataclasses like `RunPlanSpec`, using native dict serialization (`run_plan_spec_from_dict(run_plan_spec_to_dict(x))`) is a preferred performance optimization over `copy.deepcopy()` because it avoids reflection overhead and is significantly faster (~3-4x). This pattern has already been identified in other areas like `compiler_legacy.py` for standard dicts, but it natively applies to typed spec objects via their explicit serialization methods.
**Action:** When cloning complex config objects or specs, look for existing `to_dict`/`from_dict` methods to perform the clone instead of `copy.deepcopy()` to improve copy speed on hot paths.
