## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2026-01-24 - Lazy Directory Size Evaluation
**Learning:** Eagerly calculating recursive directory sizes (e.g., using `Path.rglob`) during simple file discovery imposes an O(N) penalty per directory that blocks the main thread, even when those sizes aren't universally needed.
**Action:** Replace the target size field with a private backing attribute (`_size_bytes`) and expose a `@property` that computes and caches the size via an optimized `os.scandir` recursive loop only on first access.