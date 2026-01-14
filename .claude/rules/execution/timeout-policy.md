# Timeout Policy

Timeouts prevent runaway operations. Every operation has a hard limit.

## Timeout Hierarchy

| Scope | Default | Hard Limit | Rationale |
|-------|---------|------------|-----------|
| **Flow** | 30 minutes | 45 minutes | Complete flow with all steps |
| **Step** | 10 minutes | 15 minutes | Single agent task |
| **LLM call** | 2 minutes | 3 minutes | Single model invocation |
| **Tool execution** | 5 minutes | 10 minutes | Bash, file ops, git |

### Timeout Constants

```python
TIMEOUTS = {
    "flow": 1_800_000,    # 30 minutes in ms
    "step": 600_000,      # 10 minutes in ms
    "llm_call": 120_000,  # 2 minutes in ms
    "tool": 300_000,      # 5 minutes in ms
}
```

## Nested Timeout Behavior

Timeouts cascade inward. Outer timeouts cap inner timeouts.

**Cascade rules:**
- Flow timeout triggers: all active steps terminate
- Step timeout triggers: current LLM call and tools terminate
- LLM timeout triggers: request cancelled, retry or fail

**Capping example:**
```
Remaining flow time: 5 minutes
Step timeout: 10 minutes
Effective step timeout: 5 minutes (capped by flow)
```

## Configuration Overrides

### Per-Flow Overrides

In flow spec:
```yaml
timeouts:
  step: 900000     # 15 minutes for complex flows
  llm_call: 180000 # 3 minutes for complex prompts
```

### Per-Step Overrides

For individual steps:
```yaml
steps:
  - id: heavy-analysis
    timeout_override: 1200000  # 20 minutes for this step
```

## Timeout Recovery

### State Capture on Timeout

When a timeout occurs, preserve state for resume:

```json
{
  "timeout_event": {
    "timestamp": "ISO8601",
    "scope": "step | flow | llm_call | tool",
    "timeout_ms": 600000,
    "elapsed_ms": 600123
  },
  "last_known_state": {
    "step_id": "build-step-3",
    "agent_key": "code-implementer",
    "phase": "work | finalize | route",
    "progress_indicator": "string (if available)"
  },
  "partial_artifacts": [
    {
      "path": "RUN_BASE/build/partial_impl.py",
      "complete": false,
      "bytes_written": 4523
    }
  ],
  "context_for_resume": {
    "last_successful_checkpoint": "build-step-2",
    "uncommitted_changes": ["src/auth.py", "tests/test_auth.py"],
    "transcript_path": "RUN_BASE/build/llm/step-3-partial.jsonl"
  }
}
```

### Partial Artifact Handling

On timeout:
1. Write partial receipt with `status: "timeout"`
2. Flush any buffered file writes
3. Capture git status (uncommitted changes)
4. Write transcript up to interruption point
5. Log timeout event to `RUN_BASE/<flow>/timeouts.jsonl`

### Resume Logic

```python
def resume_after_timeout(run_id, flow_key, timeout_event):
    checkpoint = timeout_event["context_for_resume"]["last_successful_checkpoint"]

    if has_uncommitted_changes(timeout_event):
        return {
            "options": ["retry_step", "discard_and_retry", "escalate"],
            "recommendation": "retry_step",
            "reason": "Partial work exists that may be salvageable"
        }
    else:
        return resume_from_step(checkpoint)
```

## Timeout Logging

All timeouts are logged to `RUN_BASE/<flow>/timeouts.jsonl`:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "run_id": "abc123",
  "flow_key": "build",
  "step_id": "step-3",
  "scope": "llm_call",
  "timeout_ms": 120000,
  "elapsed_ms": 120034,
  "retry_count": 2,
  "final_action": "escalate | retry | fail",
  "recovery_path": "RUN_BASE/build/receipts/step-3-timeout.json"
}
```

## The Rule

> Every operation has a timeout. Hard limits are non-negotiable.
> Outer timeouts cap inner timeouts. Always capture state for resume.

## Implementation Status

| Feature | Status | Location |
|---------|--------|----------|
| Step timeout | Supported | Kernel enforces via asyncio |
| LLM timeout | Supported | Transport layer |
| Flow timeout | Supported | Kernel orchestration |
| Timeout artifacts | Supported | `receipt_io.py` handles partial |
| Per-step overrides | Designed | Flow spec parsing |

---

## See Also
- [retry-policy.md](./retry-policy.md) - Retry strategies after timeout
- [circuit-breaker.md](./circuit-breaker.md) - Cascade prevention
- [resume-protocol.md](./resume-protocol.md) - Checkpoint semantics for recovery
- [error-taxonomy.md](./error-taxonomy.md) - Error classification
