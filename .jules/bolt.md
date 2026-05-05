## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-05-05 - Semantic Tests Dictate Optimization Scope
**Learning:** When replacing an O(N) filtering step (like checking file existence for 50k runs) with a deferred, lazy evaluation, existing tests might explicitly assert exact total counts rather than estimations. If a slow path (like flow_key filtering) requires exact totals for backward compatibility, you may have to preserve the original O(N) full-scan for that specific condition while optimizing the fast path.
**Action:** Before committing to a lazy evaluation strategy, verify if pagination `total` responses or specific test assertions strict-match the un-optimized, exhaustive count. Ensure fallbacks are maintained for edge cases.
