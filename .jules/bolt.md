## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-02-19 - Defer File Existence Checks II
**Learning:** Even fast `os.path.exists` or `os.path.isdir` checks are a major bottleneck when scanning directories containing thousands of items. Iterating over each item and making multiple `os.stat` calls adds significant overhead.
**Action:** Optimize directory scanning by using a nested `os.scandir` to pull all child entry names into memory as a set, and perform existence checks using standard set operations (e.g. `in` and `intersection`).
