## 2026-01-23 - Defer File Existence Checks
**Learning:** When listing items from a large directory (e.g. 50k runs), checking file existence (`os.path.exists`) for every item is a significant bottleneck, even if the check is fast.
**Action:** Sort candidates by cached metadata (e.g. mtime from `os.scandir`) first, then only perform expensive checks (like file existence or loading content) on the top N results that will actually be returned.
## 2026-06-06 - Refactor Path.iterdir() to os.scandir()
**Learning:** Checking file existence or checking if `is_dir()` on large directories using `Path.iterdir()` can be an expensive bottleneck due to extra system stat calls per item. `os.scandir()` provides an efficient alternative, accessing cached OS metadata.
**Action:** When performing large directory iterations for lists, use `os.scandir()` and read attributes directly off `os.DirEntry` to defer potentially expensive file existence checks or object instantiations to only the necessary items.
