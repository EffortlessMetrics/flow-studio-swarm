## 2025-01-26 - SSE Event Stream Path Traversal
**Vulnerability:** The `stream_run_events` endpoint in `swarm/api/routes/events.py` accepted an unvalidated `run_id` and used it to construct a file path for reading `events.jsonl`, allowing potential directory traversal (e.g., `../`).
**Learning:** Re-implementing logic (accessing `runs_root` and constructing paths manually) instead of using the centralized `SpecManager` or `RunStateManager` methods led to missing validation that existed in the centralized services.
**Prevention:** Always validate user-supplied path components using `validate_path_component` immediately upon entry at the API boundary, or prefer using centralized service methods that already include validation.
