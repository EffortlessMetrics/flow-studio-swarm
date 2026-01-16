# Truth Hierarchy

When sources conflict, higher levels override lower levels.

## The Hierarchy

1. **Physics** — exit codes, file hashes, git status (highest trust)
2. **Receipts** — captured logs, test output, scan results
3. **Intent** — specs, ADRs, BDD scenarios
4. **Artifacts** — generated code, tests, docs
5. **Narrative** — agent claims (lowest trust, never trust for routing)

## The Rule

> Routing decisions use levels 1-3. Never rely on level 5.
> Claims must cite evidence. "Not measured" is valid. False certainty is not.

## Evidence Binding

Claims require: `measured: true/false`, `evidence: <path>`, `result: <data>`.

> Full documentation: docs/explanation/TRUTH_HIERARCHY.md
