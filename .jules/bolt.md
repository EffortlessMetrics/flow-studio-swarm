## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.

## 2026-05-10 - os.scandir for directory traversal performance
**Learning:** Using `Path.iterdir()` paired with `.is_dir()` and `.name` on large directories scales poorly because it implicitly instantiates path objects and forces expensive synchronous system stat calls for every item.
**Action:** Use `os.scandir()` to efficiently leverage cached OS metadata natively via `entry.is_dir()` and `entry.name`. Only wrap the resulting string `entry.path` with `Path()` if downstream logic strictly requires it.
