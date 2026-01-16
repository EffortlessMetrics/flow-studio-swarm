# Timeout Policy

Every operation has a hard limit.

## Defaults

| Scope | Default | Hard Limit |
|-------|---------|------------|
| Flow | 30 min | 45 min |
| Step | 10 min | 15 min |
| LLM call | 2 min | 3 min |
| Tool execution | 5 min | 10 min |

## Cascade Behavior

- Outer timeouts cap inner timeouts
- Flow timeout triggers: all steps terminate
- Step timeout triggers: current LLM call and tools terminate

## On Timeout

1. Write partial receipt with `status: "timeout"`
2. Flush any buffered writes
3. Capture git status (uncommitted changes)
4. Log timeout event

## Rules

- Every operation has a timeout
- Hard limits are non-negotiable
- Always capture state for resume
