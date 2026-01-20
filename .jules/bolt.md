## 2025-01-XX - [Run Listing Scalability]
**Learning:** Loading `RunSummary` objects (reading `meta.json`) for every run just to sort them is a major bottleneck (O(N) file reads). Run IDs contain timestamps (`run-YYYYMMDD-HHMMSS-xxxxxx`), allowing O(1) sorting by ID without file I/O for the majority of runs.
**Action:** Always prefer listing and sorting by directory/file names first if they contain sortable keys (like timestamps), and defer full metadata loading to the pagination slice.
