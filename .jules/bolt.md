## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-05-06 - In-place list optimization
**Learning:** When combining two lists that need to be sorted, using `list1.extend(list2)` followed by an in-place `list1.sort()` is measurably faster and consumes less memory than `sorted(list1 + list2)`, as it avoids allocating a third intermediate list. Additionally, caching object methods like `set.add` and `list.append` in local variables before a tight loop reduces method lookup overhead.
**Action:** Look for opportunities to use in-place sorts (`.sort()`) instead of `sorted()` when list immutability is not required, and hoist method lookups out of hot loops.
