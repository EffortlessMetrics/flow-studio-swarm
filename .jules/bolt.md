## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-01-24 - Efficient Recursive Directory Size Calculation
**Learning:** For calculating recursive directory sizes efficiently, `pathlib.Path.rglob` has generator overhead and duplicate `stat` calls.
**Action:** Replace `pathlib.Path.rglob` with a recursive function using `with os.scandir(dir_path) as it:` to avoid generator overhead and reduce duplicate `stat` calls.

## 2026-01-24 - Lazy Evaluation of Dataclass Fields
**Learning:** To implement lazy evaluation in Python dataclasses, replacing the target field with a property and a backing private attribute prevents eager evaluation of expensive properties.
**Action:** Replace the target field with a private backing attribute (e.g., `_size_bytes: int = field(default=-1, repr=False)`) and expose a `@property` that computes and caches the value on first access.
