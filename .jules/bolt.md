## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2026-04-25 - Avoid copy.deepcopy on RunPlanSpec
**Learning:** `copy.deepcopy` is extremely slow on deeply nested dataclasses like `RunPlanSpec` in this application (~0.54s for 10000 iterations). Custom clone methods provide nearly an order of magnitude speedup (~0.08s for 10000 iterations).
**Action:** Implement and use custom `.clone()` methods that manually construct objects and perform shallow copies on internal collections instead of relying on `copy.deepcopy`.
