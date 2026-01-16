# Commit Guidelines

## Message Format

Subject: `<type>: <description>` (50 chars, imperative, no period)

Types: feat | fix | refactor | docs | test | chore

## Body

What and why, not how. Reference issues: `Fixes #123`

## Atomicity

One logical change per commit. Tests pass at each commit.

## Never Commit

- Multiple unrelated changes
- Generated files without source
- Secrets, credentials, API keys
- Large binaries (use LFS)

## Agent-Generated Commits

Format:
```
feat: implement OAuth2 callback handler

Receipt: swarm/runs/abc123/build/receipts/step-3-code-implementer.json
Tests: 12 passed, 0 failed
Coverage: 89% on new code

Fixes #234
```

Rules:
- Never bypass hooks (`--no-verify`)
- Evidence in body, not subject
- Standard types (no [AUTO] markers)
