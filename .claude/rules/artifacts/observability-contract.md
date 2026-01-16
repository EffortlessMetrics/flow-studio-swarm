# Observability Contract

Logs are structured, correlated, and safe.

## Required Fields
- timestamp (ISO8601), level, run_id, flow_key, step_id, agent_key, message

## Levels
ERROR (failures) | WARN (concerns) | INFO (transitions) | DEBUG (details)

## Never Log
- Secrets, API keys, passwords
- Full file contents
- PII (emails, names)
- Raw LLM responses (write to transcript file)

## Correlation
`run_id` ties everything together. Step logs are primary.

> Docs: docs/artifacts/OBSERVABILITY.md
