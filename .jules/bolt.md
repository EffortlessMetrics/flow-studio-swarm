# Bolt's Journal ⚡

## 2025-05-23 - Optimize list_runs by deferring file existence checks
**Learning:** `os.path.exists` inside a large loop (e.g. iterating 10k+ files) is a significant performance bottleneck due to syscall overhead, even if most checks are negative.
**Action:** When listing and filtering large directories, collect entries using `os.scandir` (which caches stats), sort/filter in memory using cached metadata (like `st_mtime`), and *then* perform expensive file system checks only on the top `limit` candidates. This reduced listing time by ~30% for 10k items.
