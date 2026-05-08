## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-05-08 - Optimized directory traversal with os.scandir
**Learning:** Iterating large directories using `Path.iterdir()` with `is_dir()` and `.name` introduces excessive system stat overhead by continuously creating Python Path objects and invoking `stat()` calls. For massive directories like thousands of run histories, this is a significant bottleneck.
**Action:** Used `os.scandir()` instead, which correctly avoids duplicate internal stat operations by relying on the OS's native metadata cache, yielding massive speed improvements for simple filtering steps and discovery.
