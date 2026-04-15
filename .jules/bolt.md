## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-04-15 - Optimize Directory Traversal in runs_gc
**Learning:** Replacing Path.rglob('*') with an iterative os.scandir using a stack and explicitly handling symlinks significantly improves directory traversal performance by avoiding expensive recursive stat checks.
**Action:** Use an iterative os.scandir with explicit symlink handling instead of Path.rglob for traversing potentially deep or large directory structures.
