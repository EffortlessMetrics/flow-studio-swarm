# Runbook Structure

## Purpose

Defines the required sections and writing principles for operational runbooks. A runbook must be executable by someone unfamiliar with the system.

## The Rule

> Every runbook has: Purpose, Prerequisites, Steps (with expected outputs), Verification, Rollback, and Troubleshooting. Commands are copy-pasteable. Decision points are explicit.

## What Runbooks Are (and Aren't)

Runbooks exist to:
- Enable someone unfamiliar with the system to execute safely
- Provide verifiable success criteria
- Document rollback paths before they're needed
- Capture tribal knowledge in executable form

Runbooks are NOT:
- Flow artifacts (those go to `RUN_BASE/<flow>/`)
- General documentation (those go to `docs/`)
- Agent definitions (those go to `.claude/agents/`)

## Required Sections

Every runbook MUST include these six sections:

### 1. Purpose
One sentence: what this runbook accomplishes.

### 2. Prerequisites
What must be true before starting.

### 3. Steps
Numbered steps with exact commands and expected outputs.

### 4. Verification
How to confirm the runbook succeeded.

### 5. Rollback
What to do if it fails.

### 6. Troubleshooting
Common issues and fixes.

## Section Examples

```markdown
## Purpose
Restore a failed stepwise run from its last checkpoint.

## Prerequisites
- Python 3.11+ installed
- `uv` package manager available
- Access to `swarm/runs/<run-id>/` directory

## Steps

### Step 1: Identify the last checkpoint (1 min)

```bash
ls -la swarm/runs/<run-id>/*/receipts/
```

**Expected output**: List of receipt files, one per completed step.

**Decision point**:
- If receipts exist → proceed to Step 2
- If no receipts → run is unrecoverable, start fresh

## Verification

Run:
```bash
make validate-swarm && echo "SUCCESS"
```

**Pass criteria**: Exit code 0, "SUCCESS" printed, no warnings.

## Rollback

If step 3 fails:
1. Restore the backup: `cp -r backup/ swarm/runs/<run-id>/`
2. Verify backup: `ls swarm/runs/<run-id>/`
3. Start over from Step 1

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| "Permission denied" | File locked | `chmod +w <file>` or close editor |
| "No such file" | Wrong run ID | `ls swarm/runs/` to find actual ID |
```

## Writing Principles

### Executable by the Unfamiliar

Every step must be understandable by someone who hasn't seen this system before.

**Bad:** `Now update the config as usual.`

**Good:** `Edit swarm/config/flows.yaml and add the new step. Verify: grep "new-step" swarm/config/flows.yaml returns the line.`

### Every Step Has Expected Output

Never leave the reader wondering if it worked. Show what success looks like.

**Bad:** `Run make validate-swarm.`

**Good:** `Run make validate-swarm. Expected output: "All validations passed." If you see errors, proceed to Troubleshooting.`

### Decision Points Are Explicit

Branch logic is spelled out, not assumed.

**Bad:** `Handle any issues that arise.`

**Good:**
```markdown
**Decision point**:
- If output shows "PASSED" → proceed to Step 3
- If output shows "FAILED with lint errors" → run `make auto-lint`, then repeat Step 2
- If output shows "FAILED with test errors" → proceed to Troubleshooting
```

### Commands Are Copy-Pasteable

No placeholder confusion, no assumed context. Use concrete examples.

**Bad:** `Run the command with appropriate flags.`

**Good:** `uv run swarm/tools/validate_swarm.py --strict`

### Time Estimates Are Included

Each step includes expected duration: `### Step 3: Run full validation (2 min)`

## Naming Convention

Runbook filenames follow: `<action>-<target>[-<context>].md`

| Pattern | Example | Description |
|---------|---------|-------------|
| `deploy-*` | `deploy-flow-studio.md` | Deployment procedures |
| `recover-*` | `recover-failed-run.md` | Recovery procedures |
| `rotate-*` | `rotate-api-keys.md` | Credential rotation |
| `*-health-check` | `10min-health-check.md` | Validation checks |
| `*-fastpath` | `stepwise-fastpath.md` | Quick-start guides |

---

## See Also

- [runbook-validation.md](./runbook-validation.md) - What makes a good runbook, anti-patterns
- [swarm/runbooks/README.md](../../../swarm/runbooks/README.md) - Runbook index
- [evidence-discipline.md](./evidence-discipline.md) - Why expected outputs matter
