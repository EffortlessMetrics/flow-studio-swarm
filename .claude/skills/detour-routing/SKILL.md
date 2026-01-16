---
name: detour-routing
description: Route known failure patterns to standard fixes. Use when matching error signatures to detour catalog.
---
# Detour Routing

1. Capture failure signature (error type, location, context).
2. Match against known signatures in detour catalog.
3. If match found: Route to appropriate detour handler.
4. Execute detour fix and verify resolution.
5. If fix fails twice: Escalate instead of looping.
6. Log routing decision with evidence paths.
