# Stuck Run and Wrong Output

Follow the evidence trail. Artifacts before agents.

## Stuck Run Diagnosis
1. Identify stuck step (no receipt or incomplete)
2. Check for BLOCKED status in handoff envelope
3. Check for missing inputs from previous step
4. Check routing log for unhandled ESCALATE
5. Check if microloop hit iteration limit

**Common fixes**: Provide missing input, make escalated decision, route to detour

## Wrong Output Diagnosis
1. Check evidence panel (do metrics agree?)
2. Verify inputs were correct
3. Check scent trail for bad prior decisions
4. Check assumptions in handoff envelope
5. Compare output to spec

**Common fixes**: Re-run from step with bad decision, clarify requirements

## The Rule
- Check artifacts before asking the agent
- Panel disagreement reveals problems
- Wrong assumptions = re-run from Signal

> Skill: run-diagnosis
> Docs: docs/troubleshooting/FAILED_RUNS.md
