## 2025-05-20 - Pathlib Overhead in Hot Loops
**Learning:** Pathlib's object-oriented interface introduces significant overhead (up to ~4x slower) compared to `os.scandir` and `os.path` functions when iterating large directories and checking file existence. This is due to the cost of creating Path objects for every entry.
**Action:** For performance-critical loops iterating over file systems (like listing thousands of runs), prefer `os.scandir` and `os.path` over `pathlib.Path.iterdir`.
