## 2024-05-23 - [Consolidated Directory Scanning]
**Learning:** `os.scandir` is efficient, but calling it multiple times (once for active runs, once for legacy runs) doubles the I/O overhead. Combining these checks into a single pass (`scan_runs`) reduced list time by ~50%.
**Action:** When categorizing files in a directory, always try to do it in a single pass of `os.scandir` rather than multiple filtered passes.
