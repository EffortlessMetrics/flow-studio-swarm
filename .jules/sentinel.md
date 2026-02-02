# Sentinel's Journal - Critical Security Learnings

## 2026-02-02 - API Layer Path Construction Vulnerability
**Vulnerability:** API routes (e.g., `db.py`, `evolution.py`) construct file paths from user inputs (`run_id`, `patch_id`) without validation, relying on lower layers (`ResilientStatsDB`) which only handle exceptions, not security validation.
**Learning:** `ResilientStatsDB` "safe" methods are safe from crashes (using try/except) but not safe from malicious inputs. The term "safe" is misleading in a security context.
**Prevention:** Always validate path components at the API boundary using `validate_path_component` before passing them to any file system or database layer, especially when constructing paths. Do not assume "safe" methods handle security validation.
