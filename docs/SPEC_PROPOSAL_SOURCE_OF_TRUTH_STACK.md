# The spec/proposal system, fully explained

The system is a **repo source-of-truth stack**. Its central rule is:

> **Do not make every document do every job.**

Each artifact owns one kind of truth: **why**, **what**, **what decision**, **how**, **what now**, **what proves it**, and **what changed**.

The end result is a repo where a human, Codex, Droid, Claude, or CI can answer:

```text
Why are we doing this?
What exact behavior must be true?
What architecture decision did we make?
What PR-sized work comes next?
What is the active lane right now?
What proves the claim?
Which support tier changed?
Which policy ledgers changed?
What happened after merge?
```

That is the whole system.

---

## 1) The stack at a glance

```text
Roadmap
  -> Proposal / PRD
    -> Specs
      -> ADRs where needed
        -> Implementation plan
          -> Active goal manifest
            -> Issues / PRs
              -> Proof commands
              -> CI lanes
              -> support-tier updates
              -> policy receipts
                -> Closeout / handoff
```

Each layer narrows the previous one.

- **Roadmap**: direction.
- **Proposal**: why this initiative should exist.
- **Spec**: behavior contract.
- **ADR**: architecture decision.
- **Plan**: PR sequence.
- **Active goal manifest**: what is executing now.
- **Support-tier map**: what users may believe.
- **Policy ledger**: exceptions and governed boundaries.
- **Closeout**: what actually happened.

---

## 2) Why this system exists

The point is **repo-operational memory**, not generic “better docs.”

Without this stack, teams and agents rely on stale context and assumptions. With it, the repo itself expresses the execution graph:

```text
.codex/goals/active.toml
  -> linked implementation plan
    -> linked spec
      -> linked proposal
        -> linked support-tier and policy proof
```

---

## 3) Artifact types and ownership

### 3.1 Roadmap

**Owns**: release direction, milestone themes, high-level sequencing.

**Does not own**: acceptance tests, PR order, detailed tasks.

Typical location:

```text
ROADMAP.md
docs/roadmap.md
```

### 3.2 Proposal / PRD

**Owns**: why work exists.

Typical location:

```text
docs/proposals/
```

A proposal explains problem, user value, alternatives, risks, success criteria, and linked specs/ADRs. It should not contain the full PR queue.

### 3.3 Spec

**Owns**: what behavior must be true.

Typical location:

```text
docs/specs/
```

A spec defines contract, non-goals, required evidence, test mapping, implementation mapping, and promotion rules. It should not become an implementation backlog.

### 3.4 ADR

**Owns**: durable architecture decisions.

Typical location:

```text
docs/adr/
```

Use ADRs when future work must respect a durable decision; not for every task.

### 3.5 Implementation plan

**Owns**: PR-sized sequencing.

Typical location:

```text
plans/<milestone>/
```

Plan entries should define files/surfaces affected, proof commands, rollback, claim boundary, blockers.

### 3.6 Active goal manifest

**Owns**: what agent/operator is executing now.

Typical location:

```text
.codex/goals/active.toml
.codex/goals/archive/
```

This is machine-readable execution state. Do not depend on chat transcripts for operational state.

### 3.7 Support tiers

**Owns**: product claim → proof command mapping.

Typical location:

```text
docs/status/SUPPORT_TIERS.md
```

No stable claim should exist without mapped proof.

### 3.8 Policy ledgers

**Own**: exceptions, package boundaries, CI lanes, lint policies, file policies, panic exceptions, receipts.

Typical location:

```text
policy/*.toml
ci/**/*.toml
docs/tracking/**/*.toml
```

### 3.9 Closeout / handoff

**Owns**: what actually happened.

Typical location:

```text
docs/handoffs/
plans/<milestone>/closeout.md
docs/releases/
docs/release/
```

---

## 4) Recommended directory layout

```text
docs/
  proposals/
  specs/
  adr/
  status/
  release/
  handoffs/
plans/
  <milestone>/
.codex/
  goals/
policy/
  *.toml
```

Use stable repo prefixes such as `ADZE-*`, `SHIPPER-*`, `TOKMD-*`, `BITNET-*`.

---

## 5) Link graph expectations

The stack is link-driven:

- Roadmap links to proposals.
- Proposals link to specs/ADRs/plans.
- Specs link back to proposals and forward to proof.
- ADRs link to dependent specs/plans.
- Plans link proposal/spec/ADR IDs.
- Active goals link plan work items.
- PRs link plan/spec/proposal.
- Closeouts link landed work and proof.

Recommended headers across artifacts:

```md
Status:
Owner:
Created:
Milestone:
Linked proposal:
Linked specs:
Linked ADRs:
Linked plan:
Linked issues:
Linked PRs:
Support-tier impact:
Policy impact:
```

---

## 6) Status lifecycle

- Proposals/specs/ADRs: `draft`, `proposed`, `accepted`, `implemented`, `superseded`, `rejected`
- Plan items: `ready`, `active`, `blocked`, `done`, `superseded`
- Active goals: `active`, `paused`, `complete`, `archived`

---

## 7) Anti-duplication rule

One truth, one owner:

- Claim stability: `docs/status/SUPPORT_TIERS.md`
- CI lane policy: `policy/ci-lane-whitelist.toml`
- Package classification: `policy/package-boundary.toml`
- Active lane now: `.codex/goals/active.toml`
- PR order: `plans/<milestone>/implementation-plan.md`
- Why: `docs/proposals/*`
- What: `docs/specs/*`
- Durable architecture choice: `docs/adr/*`

Duplicating the same fact across many documents guarantees drift.

---

## 8) Agent operating flow

```text
1. Read .codex/goals/active.toml.
2. Pick next ready work item.
3. Read linked plan item.
4. Read linked spec.
5. Read linked proposal for context.
6. Read linked ADRs when architecture is involved.
7. Make one PR-sized change.
8. Update support tiers/policies only if claims/policies changed.
9. Run listed proof commands.
10. Update active manifest.
11. Continue by repo policy.
12. Add closeout notes when lane completes.
```

Also: verify any named command/lint/crate/workflow/API before depending on it.

---

## 9) CI checks that make this real

Recommended checks:

```text
cargo xtask check-doc-artifacts
cargo xtask check-goals
cargo xtask check-package-boundary
cargo xtask check-ci-lanes
cargo xtask check-support-tiers
cargo xtask policy-report
```

These checks validate artifact existence, linkage, status vocabulary, proof coverage, policy integrity, and command realism.

---

## 10) PR structure

A PR should declare layer and boundaries:

- Summary
- Links (proposal/spec/ADR/plan/issue)
- Scope
- Non-goals
- Support-tier impact
- Policy impact
- Proof commands
- Claim boundary
- Rollback

Claim boundaries prevent over-promoting narrow evidence.

---

## 11) Core principles

1. One artifact, one kind of truth.
2. Specs are contracts, not queues.
3. Plans are PR-sized and executable.
4. Claims must be proof-mapped.
5. Policy exceptions must be explicit ledgers.
6. Agent state must be machine-readable.
7. Do not encode fake repo rules.
8. Verify specifics before relying on them.

---

## 12) Minimal rollout order

1. Define model and templates.
2. Add doc artifact ledger.
3. Add `check-doc-artifacts`.
4. Add active goal manifest.
5. Add `check-goals`.
6. Add first proposal.
7. Add first spec.
8. Add support tiers.
9. Add policy ledgers.
10. Wire CI (advisory first, blocking later).

---

## 13) Simplest mental model

```text
Proposal = why.
Spec = what.
ADR = durable decision.
Plan = how.
Active goal = what now.
Support tiers = what users may believe.
Policy ledgers = exceptions and proof obligations.
CI = what proved it.
Closeout = what happened.
```

The stack works when layers are linked, validated, and non-duplicative.
