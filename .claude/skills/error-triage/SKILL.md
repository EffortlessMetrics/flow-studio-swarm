---
name: error-triage
description: Classify and route errors by category (transient, permanent, retriable, fatal). Use when diagnosing failures, deciding retry vs escalate, or triggering circuit breaker.
---
# Error Triage

1. Capture error details (type, message, exit code, context).
2. Classify: transient, permanent, retriable, or fatal.
3. Transient: Retry with exponential backoff (max 5).
4. Permanent: Fail fast, capture context for diagnosis.
5. Retriable: Limited retries (max 3), no backoff.
6. Fatal: Halt immediately, preserve state for forensics.
