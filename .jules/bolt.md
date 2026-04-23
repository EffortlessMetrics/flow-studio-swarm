## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.## 2025-02-23 - Python copy.deepcopy overhead
**Learning:** `copy.deepcopy` is significantly slow in Python, especially for heavily nested dataclasses. Hand-rolling a `clone()` method that manually constructs the object and performs shallow copies on collections (`list()`) is nearly 10x faster (0.22s vs 0.025s for 10k operations).
**Action:** When a dataclass structure is well-known and needs frequent deep copies (e.g., plan specs in an SDLC loop), implement a custom `clone()` method instead of relying on the generic `copy.deepcopy`.
