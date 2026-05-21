# Contributing: Repo-Native Spec Rails

Use `.flow-studio-swarm-spec/` as the durable knowledge base for long-lived planning and contract artifacts.

## Owned scope

- `.flow-studio-swarm-spec/`
- `docs/spec-style.md`
- `docs/contributing/spec-rails.md`
- `policy/*.toml` only when referencing existing live ledgers
- `plans/` only when already part of the repo's non-agent planning surface

## Do not treat as durable rails

- `.codex/`
- `.spec/`
- `.claude/`
- `.jules/`

These are external/tool-specific state for this lane.

## Contribution checklist

1. Add or update durable artifacts under `.flow-studio-swarm-spec/`.
2. Ensure all durable artifacts are linked through `.flow-studio-swarm-spec/index.toml` conventions.
3. Keep proposal/spec/ADR/lane/closeout responsibilities separate.
4. Reference policy/support sources instead of duplicating them.
5. Avoid introducing durable ownership claims for tool-state directories.
