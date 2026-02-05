## 2025-01-26 - [StatsDB Path Traversal Gap]
**Vulnerability:** Path traversal in `StatsDBRebuildMixin.rebuild_from_events` and `rebuild_stats_db` allowed accessing files outside the runs directory via crafted `run_id`.
**Learning:** Mixins and standalone utility functions accessing the filesystem must explicitly validate path components, especially when handling IDs that map to directories.
**Prevention:** Ensure `validate_path_component` is used in all methods accepting `run_id` or similar identifiers before constructing paths, even in internal mixins or maintenance utilities.
