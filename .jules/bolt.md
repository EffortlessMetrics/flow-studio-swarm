## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2025-02-27 - Custom Clone Optimization for Nested Dataclasses
**Learning:** In heavily nested dataclasses like `RunPlanSpec`, using `copy.deepcopy` acts as a massive performance bottleneck. The overhead of Python's generic deepcopy mechanism slows down execution significantly. Implementing custom `clone()` methods that manually construct objects and perform shallow copies on internal collections provides a ~6x speedup.
**Action:** Whenever working with heavily nested dataclasses that require frequent duplication, prefer writing dedicated `clone()` methods over relying on `copy.deepcopy` to achieve significant performance gains.
