# Versioning

Versioning communicates compatibility, not vibes.

## Schemes

- Public contracts are versioned
- Backward-compat changes bump minor
- Breaking changes bump major

## Breaking Changes Require

1. Deprecation announcement
2. Migration plan
3. Compatibility window (old + new) when external dependents exist

## Internal-Only Changes

May skip lifecycle, but note why in PR.

## Rules

- If it breaks consumers, it's a breaking change
- Breaking change = major version bump + deprecation lifecycle
- Document what constitutes "breaking" for your API
