## 2026-01-20 - Path Traversal in Run Artifacts
**Vulnerability:** Path traversal vulnerability in `load_transcript` and `load_receipt` within `run_artifacts.py` allowed access to arbitrary files via crafted `flow_key` or `run_id` inputs due to unvalidated `pathlib` joins.
**Learning:** `pathlib`'s `/` operator does not sanitize `..` components, and relying on `glob` with user input is dangerous if the directory path itself is user-controlled.
**Prevention:** Always validate user-supplied path components against a strict allowlist (alphanumeric) before using them in file path construction.
