## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2026-01-24 - O(1) Directory Listing
**Learning:** For extremely large directories, `os.path.exists()` calls within `os.scandir` iteration significantly degrade performance. A fast-path directory scanner fetching all candidate names and deferring validation entirely is an order of magnitude faster.
**Action:** Implement fast-path scanners using `os.scandir()` to grab names without stat/existence checks. Defer `meta.json` validation to the lazy hydration phase within the pagination window.