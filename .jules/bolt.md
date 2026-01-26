## 2025-05-22 - [Optimizing List Filtering]
**Learning:** Checking file existence (`os.path.exists`) inside a loop over thousands of directory entries is a significant bottleneck, even if most checks fail.
**Action:** When filtering a large list of files/directories where only the top-K results are needed (e.g., sorted by mtime), sort the lightweight directory entries first, then perform the expensive checks only on the top-K candidates.
