# Circuit Breaker

Circuit breakers prevent cascading failures when a service is degraded.

## Purpose

When retries keep failing, stop trying. Give the system time to recover.

**Without circuit breaker:**
- Failing service gets hammered with retries
- Cascading failures across dependent services
- Resources wasted on doomed requests

**With circuit breaker:**
- Failing service gets breathing room
- Failures isolated, not cascaded
- Fast-fail for callers during outage

## State Machine

```
CLOSED (normal) ──[3 failures]──► OPEN (paused)
                                      │
                                  [30 sec]
                                      │
                                      ▼
                                 HALF-OPEN
                                      │
                    [success]─────────┼─────────[failure]
                        │             │              │
                        ▼             │              ▼
                    CLOSED            │           OPEN
                                      │
                              [5 total failures]
                                      │
                                      ▼
                                 ESCALATE
```

## Thresholds

| Threshold | Value | Action |
|-----------|-------|--------|
| Consecutive failures to open | 3 | Pause 30 seconds |
| Consecutive failures to escalate | 5 | Human intervention |
| Success count to reset | 1 | Resume normal operation |
| Pause duration | 30 seconds | Cooling period |

## Implementation

```python
class CircuitBreaker:
    def __init__(self):
        self.failures = 0
        self.state = "CLOSED"
        self.last_failure = None

    def record_failure(self):
        self.failures += 1
        self.last_failure = now()

        if self.failures >= 5:
            return "ESCALATE"
        elif self.failures >= 3:
            self.state = "OPEN"
            return "PAUSE"
        return "RETRY"

    def record_success(self):
        self.failures = 0
        self.state = "CLOSED"

    def can_proceed(self):
        if self.state == "CLOSED":
            return True
        if self.state == "OPEN":
            if now() - self.last_failure > 30:
                self.state = "HALF-OPEN"
                return True
            return False
        return True  # HALF-OPEN: try one request
```

## Routing Integration

Circuit breaker states map to routing decisions:

| State | Action |
|-------|--------|
| CLOSED | Normal operation |
| OPEN | Fast-fail, return cached/default if available |
| HALF-OPEN | Try one request, watch result |
| ESCALATE | Route to human intervention |

## The Rule

> After 3 consecutive failures, pause. After 5, escalate.
> One success resets the breaker. Give failing services room to recover.

## Implementation Status

| Feature | Status | Location |
|---------|--------|----------|
| Circuit breaker | Designed | Kernel would implement |
| State tracking | Designed | Per-service breakers |
| Escalation routing | Designed | Navigator integration |

---

## See Also
- [retry-policy.md](./retry-policy.md) - Retry strategies before circuit opens
- [timeout-policy.md](./timeout-policy.md) - Timeout hierarchy
- [error-taxonomy.md](./error-taxonomy.md) - Error classification
- [routing-decisions.md](./routing-decisions.md) - ESCALATE decision
