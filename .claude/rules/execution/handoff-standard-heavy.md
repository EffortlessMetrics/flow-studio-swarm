# Standard and Heavy Handoffs

Standard: step-to-step within flow. Heavy: flow boundaries.

## Standard Handoff (500-2000 tokens)
Include:
- meta: step_id, agent_key
- summary: what_i_did, what_i_found, key_decisions, evidence
- assumptions: explicit with rationale and impact
- routing: recommendation + reason

## Heavy Handoff (2000-5000 tokens)
Standard fields plus:
- plan_summary: work_items count, complexity, key_interfaces
- dependencies: what to install before coding
- test_strategy: approach for test authors

## The Rule
- Standard: between consecutive steps
- Heavy: at flow boundaries (Plan→Build, Gate→Deploy)
- Always use pointers, not inline content
- Re-explaining prior decisions = bloat (use scent trail)

> Docs: docs/execution/HANDOFF_PROTOCOL.md
