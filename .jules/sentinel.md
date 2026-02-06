# Sentinel Journal

## 2025-01-20 - Missing Path Traversal Validation in API
**Vulnerability:** Path traversal in `swarm/api/routes/events.py` due to unvalidated `run_id`.
**Learning:** Even if `validate_path_component` utility exists, developers might forget to use it.
**Prevention:** Use a lint rule or middleware to enforce validation on all path parameters used in file operations, or use a secure-by-default wrapper for file access.
