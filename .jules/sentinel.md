## 2026-01-21 - Shell Injection via Environment Variable Inline Assignment
**Vulnerability:** Found `subprocess.Popen(["sh", "-c", f"RUN_ID={run_id} {cmd}"])` in `ClaudeHarnessBackend`. This allows command injection if `run_id` contains shell metacharacters like `; rm -rf /`.
**Learning:** Even when `run_id` is seemingly internal or generated, if it can be influenced by input params (e.g. `spec.params`), it becomes a vector. Passing environment variables via `env` argument in `subprocess` is much safer than inline assignment in a shell string.
**Prevention:** Always use the `env` argument of `subprocess.Popen` to pass environment variables. Avoid `sh -c` unless absolutely necessary, and never interpolate untrusted data into the shell string.
