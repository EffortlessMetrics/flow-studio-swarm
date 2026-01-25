## 2025-05-23 - Run State Manager Listing Optimization
**Learning:** `os.scandir` is fast, but calling `os.path.exists` on every entry defeats the purpose if you only need the top K results.
**Action:** When listing recent items from large directories, always collect `(mtime, entry)` tuples first, sort them, and *then* perform expensive checks (like file existence or JSON parsing) only on the top K results. This reduces syscalls from $O(N)$ to $O(K)$.
