## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2026-01-24 - Lazy Evaluation and os.scandir in GC
**Learning:** Discovering large numbers of runs for Garbage Collection (GC) can be slow due to deep file stat calls (e.g. `rglob` for directory sizes) and reading metadata from every directory. However, many elements might be simply kept or skipped due to basic retention rules like max counts or dates based purely on modification time.
**Action:** Use `os.scandir` to quickly retrieve metadata (like `st_mtime`) and use lazy properties (via `@property`) to defer expensive operations (like `size_bytes` calculation and metadata parsing) until they are strictly necessary for evaluation.