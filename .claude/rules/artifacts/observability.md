# Observability

Logs are JSONL, correlated by run_id, and safe.

## Required Fields

timestamp (ISO8601), level, run_id, flow_key, step_id, agent_key, message

## Levels

ERROR (failures) | WARN (concerns) | INFO (transitions) | DEBUG (details)

## Never Log

- Secrets, API keys, passwords
- Full file contents
- PII (emails, names)
- Raw LLM responses (write to transcript file)

## The Rule

- Log events, not content. Log paths, not files.
- `run_id` correlates across everything
- Step logs are primary: `RUN_BASE/<flow>/logs/<step_id>.jsonl`
- Redact before write

> Docs: docs/artifacts/OBSERVABILITY.md
