## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-06-10 - Optimize large directory sorting with os.scandir
**Learning:** Using `sorted(Path.iterdir())` is highly inefficient for large directories because it instantiates a `Path` object for every entry before sorting. Benchmarks show a 17x speedup when using `os.scandir()` to collect string names, sorting them, and then instantiating `Path` objects only for the needed subset (especially when combined with a break/limit).
**Action:** Default to `os.scandir()` instead of `iterdir()` when sorting directory contents.
## 2026-06-10 - Fix stale tests when doing UI optimizations
**Learning:** Adding new DOM elements directly to frontend build artifacts () requires ensuring any integration tests checking for  or unique IDs () are also satisfied.
**Action:** Include ARIA labels on utility or dynamically replaced button placeholders when making quick frontend tweaks.

## $(date +%Y-%m-%d) - Fix stale tests when doing UI optimizations
**Learning:** Adding new DOM elements directly to frontend build artifacts (`index.html`) requires ensuring any integration tests checking for `aria-label` or unique IDs (`test_flow_studio_a11y.py`) are also satisfied.
**Action:** Include ARIA labels on utility or dynamically replaced button placeholders when making quick frontend tweaks.
