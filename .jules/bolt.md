## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2025-02-27 - deepcopy overhead on Dataclasses
**Learning:** `copy.deepcopy` is notoriously slow when applied to heavily nested dataclasses like `RunPlanSpec`. Using a custom `.clone()` method to manually copy fields and shallow-copy lists provides an order of magnitude (~7.6x) speedup.
**Action:** Always implement custom `.clone()` methods on dataclasses that are frequently duplicated instead of relying on the standard library `copy.deepcopy`.
