## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2025-05-18 - Replacing deepcopy with dataclasses.replace
**Learning:** Deepcopy is a major bottleneck on nested dataclasses. Using dataclasses.replace to only update the exact path being mutated avoids deepcopy overhead while safely allowing the rest of the object to share references. If full serialization is needed, use json conversion which is ~2-3x faster than deepcopy.
**Action:** Use dataclasses.replace to only update the specific field path, or use json dict conversion for full clones.
