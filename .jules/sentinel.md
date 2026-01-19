## 2024-05-23 - Path Traversal in Run Artifacts
**Vulnerability:** Run artifacts (transcripts, receipts) were accessed using unvalidated user inputs (`run_id`, `flow_key`, `step_id`), allowing path traversal attacks via `..` sequences.
**Learning:** `pathlib`'s `/` operator does not prevent traversal if the component itself contains `..`. Concatenating user input into paths without validation is always unsafe.
**Prevention:** Always use `validate_path_component` from `swarm.runtime.safe_paths` before using any user input in file paths.
