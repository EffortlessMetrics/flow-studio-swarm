# Agent-Generated Commits

Agent commits must include receipt references.

## Format
```
feat: implement OAuth2 callback handler

Receipt: swarm/runs/abc123/build/receipts/step-3-code-implementer.json
Tests: 12 passed, 0 failed
Coverage: 89% on new code

Fixes #234
```

## Rules
- Never bypass hooks (`--no-verify`)
- Standard types only (no [AUTO] or AI: markers)
- Evidence in body, not subject

> Docs: docs/safety/COMMIT_GUIDELINES.md
