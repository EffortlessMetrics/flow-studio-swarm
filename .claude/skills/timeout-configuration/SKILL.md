---
name: timeout-configuration
description: Configure appropriate timeouts for operations. Use when setting up execution limits or diagnosing timeout issues.
---
# Timeout Configuration

1. Identify operation scope (flow, step, LLM call, tool).
2. Apply defaults: flow 30m, step 10m, LLM 2m, tool 5m.
3. Hard limits cap soft limits (flow 45m, step 15m, LLM 3m, tool 10m).
4. On timeout: Write partial receipt, flush buffers, capture git status.
5. Outer timeouts cascade to inner operations.
6. Always capture state for resume capability.
