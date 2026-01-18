## 2026-01-18 - File I/O Bottleneck in Run Listing
**Learning:** `storage.list_runs` combined with `storage.read_summary` creates an N+1 file I/O problem when listing runs, as it reads every JSON file.
**Action:** Implement caching for immutable data (like terminal run summaries) in the service layer to avoid repeated disk reads.
