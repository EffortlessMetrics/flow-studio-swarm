## 2025-05-20 - Pathlib Overhead in Hot Loops
**Learning:** Pathlib's object-oriented interface introduces significant overhead (up to ~4x slower) compared to `os.scandir` and `os.path` functions when iterating large directories and checking file existence. This is due to the cost of creating Path objects for every entry.
**Action:** For performance-critical loops iterating over file systems (like listing thousands of runs), prefer `os.scandir` and `os.path` over `pathlib.Path.iterdir`.

## 2025-05-20 - Single-Pass Directory Scanning
**Learning:** When needing to classify items in a large directory into multiple categories (e.g., active vs legacy runs), doing multiple passes (one for each category) is inefficient. A single-pass approach using `os.scandir` that classifies items on the fly is significantly more efficient, especially for file system operations.
**Action:** Refactor multiple `list_*` functions that iterate over the same directory into a single `scan_*` function that returns classified results in one go.
