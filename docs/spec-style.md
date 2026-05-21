# Spec Style and Source-of-Truth Stack

This repository keeps a full source-of-truth stack, with each artifact owning one layer of intent:

- Roadmap
- Proposal / PRD
- Spec
- ADR
- Lane tracker / implementation plan
- PRs and proof commands
- Support-tier and policy references
- Closeout

## Durable home

Durable rails live under:

- `.flow-studio-swarm-spec/`

Human-facing explanation and contribution guidance live under:

- `docs/`

Live enforcement ledgers remain under:

- `policy/` (when present)

## External state boundaries

The following directories are external/tool-specific state and are not durable spec rails:

- `.codex/`
- `.spec/`
- `.claude/`
- `.jules/`

Agents may read the durable namespace, but this spec style does not manage agent scratch state.

## Separation rule

Do not collapse proposal, spec, tasks, release proof, and policy into one file. Keep artifacts separated by responsibility:

- Proposal explains why and success criteria.
- Spec defines required behavior and evidence.
- ADR records durable architecture decisions.
- Lane artifacts define PR-sized execution state.
- Closeouts capture what happened and what remains.
