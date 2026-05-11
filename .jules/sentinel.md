
## 2026-05-11 - Prevent eval and exec in production
**Vulnerability:** Code injection via `eval` and `exec`.
**Learning:** `eval` and `exec` were not explicitly forbidden by test guardrails, leaving the codebase vulnerable to accidental introduction of code injection risks.
**Prevention:** Added `test_eval_exec_guardrail.py` to block `eval()` and `exec()` in production code.
