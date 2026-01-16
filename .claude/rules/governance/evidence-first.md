# Evidence First

Don't listen to the worker; measure the bolt.

## Trust Hierarchy

1. **Physics** — exit codes, file hashes, git status
2. **Receipts** — captured logs, test output, scan results
3. **Intent** — specs, ADRs, BDD scenarios
4. **Artifacts** — generated code, tests, docs
5. **Narrative** — agent claims (never trust for routing)

## The Rule

- Routing decisions use levels 1-3. Never rely on level 5.
- Claims require evidence binding: `measured: true/false`, `evidence: <path>`, `result: <data>`
- "Not measured" is valid. False certainty is not.
- Tests require: command run, exit code, captured output path, scope
- If not measured: state NOT MEASURED, set UNVERIFIED

> Docs: docs/explanation/FORENSICS_OVER_TESTIMONY.md
