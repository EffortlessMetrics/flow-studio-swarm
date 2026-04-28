## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2025-04-28 - Replace deepcopy with clone for heavily nested dataclasses
**Learning:** Using copy.deepcopy on heavily nested dataclasses like NavigatorOutput introduces significant performance bottlenecks, running ~15x slower than manual cloning due to recursion and reflection overheads in Python.
**Action:** When copying complex domain objects, implement explicit clone() methods that construct objects and perform shallow copies of internal lists/dicts instead of relying on standard library deepcopy.

## 2025-04-28 - Replace deepcopy with dataclasses.replace for dataclasses
**Learning:** Using copy.deepcopy on heavily nested dataclasses like NavigatorOutput introduces significant performance bottlenecks, running ~15x slower than manual cloning due to recursion and reflection overheads in Python.
**Action:** When copying complex domain objects that are dataclasses, use dataclasses.replace() which constructs objects explicitly and is much faster than relying on standard library deepcopy.
