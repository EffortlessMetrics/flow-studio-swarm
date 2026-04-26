## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2026-04-26 - Python deepcopy bottleneck in dataclasses
**Learning:** Using copy.deepcopy() on heavily nested dataclasses (like RunPlanSpec) is a significant performance anti-pattern, causing measurable slowdowns. Using manual instantiation for cloning yields approximately a 5x speedup.
**Action:** Always implement custom clone() methods that manually construct new objects and perform shallow copies on their internal collections for complex domain objects instead of relying on copy.deepcopy().
