## 2025-02-18 - Path Traversal Vulnerability in `step_id` Parameter

**Vulnerability:** The `get_step_status` function in `swarm/tools/run_inspector.py` was vulnerable to path traversal because the `step_id` parameter was not validated before being used to retrieve flow step configuration or access potential artifact paths. While `flow_key` and `run_id` were validated, `step_id` was overlooked.
**Learning:** Security validation must be applied uniformly to *all* path components or dictionary keys derived from user input that dictate file or data retrieval. Framework-level protections do not cover deep internal method arguments.
**Prevention:** Always comprehensively audit every parameter in functions handling file paths or configuration keys. Implement uniform validation (e.g., `validate_path_component`) for all input components immediately at the top of the function.
