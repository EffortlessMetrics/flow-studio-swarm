## 2026-01-23 - [Defer Stat Calls in os.scandir Loops]
**Learning:** `os.scandir` is fast, but calling `os.path.exists` or `os.stat` inside the loop for every entry negates the performance benefit, especially on network drives or large directories.
**Action:** Collect entries first (using cached `entry.stat()` from `scandir` if needed), sort/filter in memory, and only perform expensive filesystem checks on the top N results.
