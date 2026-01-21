## 2025-05-15 - Command Injection in Backend Harness
**Vulnerability:** The `ClaudeHarnessBackend` constructed shell commands using f-strings with user-controllable `run_id` (`sh -c "RUN_ID={run_id} ..."`), allowing command injection.
**Learning:** Even internal backends triggered by "spec" objects must treat parameters as untrusted. `sh -c` wrappers are dangerous when combining environment variable setting with command execution.
**Prevention:** Use `subprocess.Popen` with `shell=False` and pass environment variables via the `env` parameter, never via inline shell assignments.
