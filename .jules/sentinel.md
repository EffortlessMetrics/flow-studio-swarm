## 2025-05-27 - Shadow Fork Git Ref Injection
**Vulnerability:** `ShadowFork` methods accepted branch names without validation, potentially allowing argument injection in `git` commands (e.g., passing `-f` as a branch name).
**Learning:** `subprocess.run` with `shell=False` prevents shell injection but does NOT prevent argument injection if the command (like `git`) interprets arguments starting with `-` as options. Git reference names should always be validated against a strict allowlist.
**Prevention:** Implemented `validate_git_ref_format` in `safe_paths.py` and applied it to `ShadowFork` inputs. Also discovered that `test_shadow_fork.py` had incorrect mock expectations, highlighting the importance of verifying test logic against actual code execution paths.
