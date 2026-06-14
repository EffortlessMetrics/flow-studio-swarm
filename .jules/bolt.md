## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2025-06-14 - Optimize Path.iterdir() with os.scandir()
**Learning:** When scanning large directories (like runs histories), iterating with `Path.iterdir()` invokes expensive system stat calls if `.is_dir()` is subsequently called on every yielded `Path` object, and it unconditionally instantiates heavy `Path` objects. This creates a significant performance bottleneck.
**Action:** Replace `Path.iterdir()` with `os.scandir()` wrapped in a `with` context manager. Use `os.DirEntry` objects which cache stat attributes, allowing efficient pre-filtering (e.g., `if e.is_dir()`) *before* constructing heavy `Path` objects (via `parent_dir / e.name`), while being extremely careful to mirror the exact sorting/slicing logic of the original code.
