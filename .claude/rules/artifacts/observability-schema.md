# Observability Schema

All logs use JSON Lines (JSONL). One JSON object per line.

## Required Fields
- `timestamp`: ISO8601
- `level`: INFO | WARN | ERROR | DEBUG
- `run_id`: unique run identifier
- `flow_key`: signal | plan | build | review | gate | deploy | wisdom
- `step_id`: current step
- `agent_key`: active agent
- `message`: human-readable description

## Log Levels
| Level | Use |
|-------|-----|
| ERROR | Failures needing attention |
| WARN | Concerns that don't block |
| INFO | Step transitions, key decisions |
| DEBUG | Detailed execution (off by default) |

## The Rule
- All logs are JSONL
- Required fields enable querying
- Levels indicate severity
- Events categorize entries

> Docs: docs/artifacts/OBSERVABILITY.md
