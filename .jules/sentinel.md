## 2026-01-21 - Command Injection in Backend Harness
**Vulnerability:** The `ClaudeHarnessBackend` constructed shell commands using f-strings with user-controllable `run_id` (`sh -c "RUN_ID={run_id} ..."`), allowing command injection.
**Learning:** Even internal backends triggered by "spec" objects must treat parameters as untrusted. `sh -c` wrappers are dangerous when combining environment variable setting with command execution.
**Prevention:** Use `subprocess.Popen` with `shell=False` and pass environment variables via the `env` parameter, never via inline shell assignments.

## 2026-10-18 - RCE via `command` parameter in `RunSpec`
**Vulnerability:** `ClaudeHarnessBackend` and `GeminiCliBackend` honored a `command` parameter in the `RunSpec` params, passing it directly to `subprocess.Popen` (via `shlex.split`). This allowed any user with access to the API to execute arbitrary commands on the server.
**Learning:** "Debug" or "Testing" features that allow arbitrary command execution are extremely dangerous and should not be present in production code paths, even if they are intended for internal use.
**Prevention:** Strictly validate or ignore command overrides in backend logic. Ensure that data structures coming from the API (like `params`) do not directly control execution paths without strict allowlisting.
