# Sentinel Security Journal

Security findings and vulnerability notes from Jules security scanning.

---

## 2026-01-22 - Arbitrary Command Execution via API Params
**Vulnerability:** The backends allowed an optional `command` parameter in `RunSpec.params` that was passed directly to `subprocess.Popen` (even with `shell=False`).
**Learning:** `shell=False` protects against shell syntax injection, but NOT against arbitrary command execution if the executable itself (or arguments) is user-controlled.
**Prevention:** Never allow API users to specify the command or arguments passed to `subprocess`. Use strict allowlists or predefined commands.

---

## 2026-01-21 - Command Injection in Backend Harness
**Vulnerability:** The `ClaudeHarnessBackend` constructed shell commands using f-strings with user-controllable `run_id` (`sh -c "RUN_ID={run_id} ..."`), allowing command injection.
**Learning:** Even internal backends triggered by "spec" objects must treat parameters as untrusted. `sh -c` wrappers are dangerous when combining environment variable setting with command execution.
**Prevention:** Use `subprocess.Popen` with `shell=False` and pass environment variables via the `env` parameter, never via inline shell assignments.

---

## 2024-01-21 - Path Traversal Vulnerability in SpecManager and RunStateManager
**Vulnerability:** `SpecManager.get_flow`, `SpecManager.get_template`, and `RunStateManager.create_run` directly used user-provided identifiers to construct file paths without validation, allowing directory traversal (e.g., `../../target`).
**Learning:** `pathlib.Path` using the `/` operator does not automatically sanitize `..` components. Explicit validation is required before using user input in path construction. The existence of `validate_path_component` in `safe_paths.py` suggests this was known but not applied consistently.
**Prevention:** Always validate any user input used for file path construction using `validate_path_component` or similar allowlist-based validation before passing it to filesystem operations.
