# Narrow Trust

Trust = Narrowness × Evidence × Verification

## The Rule

> Prefer narrow scope with strong evidence over broad scope with weak evidence.
> A narrow agent with strong evidence is more trustworthy than a broad agent with weak evidence.

## Evidence Quality Tiers

1. **Physics**: Exit codes, file hashes, git status (highest)
2. **Receipts**: Captured logs, test output, scan results
3. **Artifacts**: Generated files, diffs
4. **Narrative**: Agent prose, claims (lowest—never trust for routing)

## Application

- Route to specialists, not generalists
- Require evidence proportional to scope
- Weight evidence by source (physics > narrative)
- Discount broad claims without narrow proof

> Docs: docs/explanation/NARROW_TRUST.md
