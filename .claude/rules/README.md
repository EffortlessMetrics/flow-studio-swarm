# AgOps Rules Registry

This directory contains the governance rules for Flow Studio's agentic operations.
These rules encode Steven Zimmerman's AI-native development philosophy: **trade compute for senior attention**.

## Rule Categories

| Directory | Purpose | Enforcement |
|-----------|---------|-------------|
| `governance/` | Agent behavioral contracts, state machines, error handling | Agent prompts + validation |
| `execution/` | Context budgets, routing decisions, microloop limits | Runtime kernel |
| `artifacts/` | Receipt schemas, handoff protocols, audit trails | `receipt_io.py` + validation |
| `safety/` | Git safety, branch protection, secrets, permissions | Hooks + boundary agents |

## Core Principle

**Rules are constitution; docs are textbook.**

- Rules define what MUST happen (enforced)
- Docs explain WHY it happens (teaching)
- Pack-check validates COMPETENCE, not schema compliance

## The Physics Stack

Rules encode the "physics" that make autonomous operation safe:

1. **Truth Hierarchy** - What counts as evidence (physics > receipts > narrative)
2. **Session Amnesia** - Each step starts fresh; disk is memory
3. **Mechanical Truth** - Never ask models to judge success; measure it
4. **Contained Blast Radius** - Work can be destructive inside the sandbox; publishing is gated
5. **Bounded Routing** - Kernel generates candidates; Navigator selects; kernel validates

## Usage

Rules are automatically loaded by Claude Code from this directory.
Path-specific rules use frontmatter to scope application.

See [docs/AGOPS_MANIFESTO.md](../../docs/AGOPS_MANIFESTO.md) for the full philosophy.
