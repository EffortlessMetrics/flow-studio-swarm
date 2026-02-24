## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2026-01-23 - Lazy Directory Size Calculation
**Learning:** Recursively calculating directory sizes (`rglob` + `stat`) is extremely expensive and dominates the runtime of file management tools like garbage collectors, even if only a few items are eventually acted upon.
**Action:** Implement lazy evaluation or an opt-in flag (e.g., `compute_size=False`) for discovery functions. Only compute the size for the specific subset of items that require it (e.g., candidates for deletion) after filtering by cheaper criteria like timestamp.
