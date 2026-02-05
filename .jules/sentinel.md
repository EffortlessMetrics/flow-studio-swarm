## 2024-05-22 - Path Traversal in Event Streaming
**Vulnerability:** Unvalidated `run_id` path parameter in `stream_run_events` endpoint allowed directory traversal (e.g., `../../secret`) to access arbitrary files on the system via `generate_run_events`.
**Learning:** While `RunStateManager` handles path validation for most run operations, the events streaming endpoint was implemented independently and bypassed the secure abstraction layer, manually constructing file paths from user input.
**Prevention:** Always use the centralized `RunStateManager` or `validate_path_component` utility when handling file paths derived from user input. Avoid manual path construction in API endpoints.
