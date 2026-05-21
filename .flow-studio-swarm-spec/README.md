# flow-studio-swarm Durable Spec Namespace

This directory is the durable, repo-owned source of truth for proposal/spec/ADR/lane/closeout rails.

## Ownership

Owned by this repository's long-term control-plane method:

- `proposals/` for problem framing and product rationale.
- `specs/` for behavior contracts and required evidence.
- `adr/` for durable architecture decisions.
- `lanes/` for focused implementation trackers and execution plans.
- `support/` for claim-to-proof mapping (or references).
- `policy/` for references to live `policy/*.toml` ledgers.
- `closeouts/` for durable memory of what landed and what remains.

## External/tool namespaces

The following directories may exist in the repo, but they are awareness-only for this system:

- `.codex/`
- `.spec/`
- `.claude/`
- `.jules/`

This namespace does not own or mutate tool-specific scratch or session state.
