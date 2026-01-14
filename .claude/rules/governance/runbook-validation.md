# Runbook Validation

## Purpose

Defines what makes a runbook good, common anti-patterns to avoid, and how to test runbooks before publishing.

## The Rule

> A runbook is only good if someone who's never seen the system can execute it successfully. Test it before publishing. Every question becomes documentation.

## What Makes a Good Runbook

| Property | Why It Matters |
|----------|----------------|
| **Idempotent** | Safe to run twice without harm |
| **Atomic steps** | Can stop and resume at any step |
| **Clear success criteria** | Know when you're done |
| **Explicit failure handling** | Know what to do when it breaks |
| **Time-bounded** | Know how long it takes |

## Anti-Patterns

### "Use Your Judgment"

**Problem:** Judgment varies. Results vary.

**Fix:** Be explicit about the decision criteria.

```markdown
# Bad
Use your judgment to decide if the output looks correct.

# Good
**Decision criteria**:
- Exit code is 0: proceed
- Exit code is 1 with "lint" in output: run auto-linter
- Any other failure: stop and escalate
```

### Missing Expected Outputs

**Problem:** Reader doesn't know if it worked.

**Fix:** Show what success looks like.

```markdown
# Bad
Run the tests.

# Good
Run:
```bash
uv run pytest tests/ -v
```

**Expected output** (truncated):
```
tests/test_validate_swarm.py::test_bijection PASSED
tests/test_validate_swarm.py::test_frontmatter PASSED
...
===== 42 passed in 3.21s =====
```
```

### Assumed Context

**Problem:** Works for you, fails for others.

**Fix:** State all prerequisites and working directory.

```markdown
# Bad
Run the validation script.

# Good
From the repository root (`flow-studio-swarm/`):
```bash
uv run swarm/tools/validate_swarm.py
```

Requires: `uv` installed, dependencies synced (`uv sync --frozen`).
```

### No Rollback Plan

**Problem:** When it fails, panic ensues.

**Fix:** Plan the retreat before the advance.

```markdown
# Bad
(Rollback section missing)

# Good
## Rollback

Before Step 3, create a backup:
```bash
cp -r swarm/runs/<run-id> swarm/runs/<run-id>.bak
```

If Step 3 fails:
```bash
rm -rf swarm/runs/<run-id>
mv swarm/runs/<run-id>.bak swarm/runs/<run-id>
```
```

### Vague Placeholders

**Problem:** Reader doesn't know what to substitute.

**Fix:** Use concrete examples with clear placeholder markers.

```markdown
# Bad
Run: `command <options>`

# Good
Run (replace `abc123` with your actual run ID):
```bash
ls swarm/runs/abc123/build/receipts/
```
```

## Testing Runbooks

Before publishing a runbook:

1. **Execute it yourself** - Run through every step manually
2. **Have someone unfamiliar execute it** - Watch where they get stuck
3. **Update based on friction** - Every question becomes documentation
4. **Verify idempotence** - Run it twice, confirm no harm

### The Friction Test

If the person executing asks:
- "What do I put here?" → Placeholder is unclear
- "Did it work?" → Expected output is missing
- "What now?" → Decision point is missing
- "What if this happens?" → Troubleshooting is incomplete

Every question reveals a documentation gap.

### Idempotence Check

A good runbook can be run twice without causing harm:

```bash
# First run
./runbook-steps.sh  # Creates resources

# Second run (should be safe)
./runbook-steps.sh  # Should handle existing resources gracefully
```

If running twice breaks things, add guards or explicit cleanup steps.

## Enforcement

Runbooks are reviewed for:
- All six required sections present
- Expected output shown for each step
- Decision points explicitly documented
- Rollback plan exists
- Time estimates included

---

## See Also

- [runbook-structure.md](./runbook-structure.md) - Required sections and writing principles
- [swarm/runbooks/README.md](../../../swarm/runbooks/README.md) - Runbook index
- [pack-check-philosophy.md](./pack-check-philosophy.md) - Competence over compliance
