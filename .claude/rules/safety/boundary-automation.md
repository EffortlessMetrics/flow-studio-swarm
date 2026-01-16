# Boundary Automation

Enforcement at publish boundary only, not inside the sandbox.

## Shadow Fork (Flows 1-5)
- Full autonomy
- All git operations permitted
- Agents work blind to upstream
- This is an isolated sandbox

## Publish Boundary (Flow 6)
- Secrets scanning before push
- Evidence verification
- No force push to upstream
- Human approval for merge

## What's Checked at Boundary
- Secret patterns in diff → BLOCK
- Evidence exists and fresh → required for merge recommendation
- All HIGH concerns addressed → required

## The Rule
- Inside sandbox: default-allow
- At boundary: fail-closed with mechanical checks
- Flow 8 handles deliberate upstream sync

> Docs: docs/explanation/BOUNDARY_PHYSICS.md
