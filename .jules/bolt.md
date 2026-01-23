# Bolt's Journal ⚡

## 2025-02-18 - File Existence Check Bottleneck in Run Listing
**Learning:** `os.path.exists` checks inside a large `os.scandir` loop significantly degrade performance when listing runs, as it forces a syscall for every directory.
**Action:** When listing recent items from a large set of directories, collect and sort candidates by directory metadata (mtime) first, then perform expensive validity checks only on the top N candidates.
