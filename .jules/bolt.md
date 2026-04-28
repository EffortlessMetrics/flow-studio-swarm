## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.## 2024-05-18 - Avoid deepcopy on heavily nested dataclasses
**Learning:** Python's `copy.deepcopy` has a massive overhead on heavily nested dataclasses like `NavigatorOutput`.
**Action:** Implemented custom `.clone()` methods that construct instances manually, performing shallow copies of inner collections. This results in ~10x speedup for these specific objects.
