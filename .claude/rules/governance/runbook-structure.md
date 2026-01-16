# Runbook Structure

Runbooks are executable checklists.

## Required Sections
| Section | Purpose |
|---------|---------|
| **Purpose** | What this accomplishes (1-2 lines) |
| **Prerequisites** | What must be true before starting |
| **Steps** | Numbered, one action per step |
| **Verification** | Commands + expected signals |
| **Rollback** | How to undo safely |
| **Troubleshooting** | Common issues and fixes |

## Writing Principles
- Steps MUST be **imperative** and **bounded**
- Verification MUST name **commands** and **evidence paths**
- "Seems fine" / "should work" is banned

## The Rule
- If a human cannot follow it linearly, it's not a runbook
- Every step has expected output
- Decision points are explicit

> Docs: docs/runbooks/RUNBOOK_STRUCTURE.md
