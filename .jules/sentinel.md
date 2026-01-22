## 2026-01-21 - Command Injection in Backend Harness
**Vulnerability:** The `ClaudeHarnessBackend` constructed shell commands using f-strings with user-controllable `run_id` (`sh -c "RUN_ID={run_id} ..."`), allowing command injection.
**Learning:** Even internal backends triggered by "spec" objects must treat parameters as untrusted. `sh -c` wrappers are dangerous when combining environment variable setting with command execution.
**Prevention:** Use `subprocess.Popen` with `shell=False` and pass environment variables via the `env` parameter, never via inline shell assignments.

## 2026-10-18 - Unchecked File Creation in Issue Ingestion
**Vulnerability:** The `ingest_issue` endpoint used user-provided `repo` input to construct a `run_id` and created directories before validating the `run_id` against the allowlist. This allowed creation of garbage directories or potential traversal attempts (though mitigated by filename structure) before the validation logic in `create_run` was triggered.
**Learning:** Input validation must occur *before* any side effects (like file creation), not just before the "main" operation.
**Prevention:** Validate all constructed paths/IDs immediately after generation and before any filesystem operations.
