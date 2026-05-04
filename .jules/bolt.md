## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2025-05-18 - Avoid deepcopy on nested dataclasses
**Learning:** Using `copy.deepcopy` on nested dataclasses like `NavigatorOutput` can be a significant performance bottleneck (e.g., 38ms vs 5ms per call) due to introspection overhead.
**Action:** Use `dataclasses.replace` targeting the specific nested fields that need mutation. This preserves the original object while safely updating only what is necessary, without the full cloning penalty.
