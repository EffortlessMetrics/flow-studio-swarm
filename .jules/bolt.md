## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2024-06-27 - Optimize Dataclass Deepcopy
**Learning:** Using dict serialization methods (to_dict/from_dict) is significantly faster (~3-4x) than copy.deepcopy() for dataclasses due to reflection overhead.
**Action:** Use native serialization for deep copying complex dataclasses instead of copy.deepcopy.
