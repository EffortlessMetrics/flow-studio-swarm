## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2024-05-24 - Replace deepcopy on nested dataclasses
**Learning:** Using `copy.deepcopy` on heavily nested dataclasses is a known performance anti-pattern.
**Action:** Either use `dataclasses.replace()` to selectively update mutated paths or use JSON serialization (e.g. `run_plan_spec_from_dict(run_plan_spec_to_dict(obj))`) for full clones.
