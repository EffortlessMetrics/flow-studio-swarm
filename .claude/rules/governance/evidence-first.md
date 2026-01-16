# Evidence First

Don't listen to the worker; measure the bolt. Trust = Narrowness × Evidence × Verification.

## Trust Hierarchy (highest → lowest)

1. **Physics** — exit codes, file hashes, git status
2. **Receipts** — captured logs, test output, scan results
3. **Intent** — specs, ADRs, BDD scenarios
4. **Artifacts** — generated code, tests, docs
5. **Narrative** — agent claims (never trust for routing)

## Narrow Trust Principle

Prefer narrow scope with strong evidence over broad scope with weak evidence.
A narrow agent with strong evidence is more trustworthy than a broad agent with weak evidence.

## The Rule

- When sources conflict, higher level wins
- Routing decisions use levels 1-3. Never rely on level 5.
- Claims require evidence binding: `measured: true/false`, `evidence: <path>`, `result: <data>`
- "Not measured" is valid. False certainty is not.
- Route to specialists, not generalists
- Discount broad claims without narrow proof

> Docs: docs/explanation/FORENSICS_OVER_TESTIMONY.md
