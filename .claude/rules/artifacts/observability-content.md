# Observability Content

Log events, not content. Log paths, not files.

## Always Log
- Step start/end with timestamps
- Routing decisions
- Error details (type, message, evidence path)
- Token usage (prompt, completion, total)
- Exit codes
- Durations

## Never Log
- Secrets (API keys, passwords, tokens)
- Full file contents
- PII (emails, names, addresses)
- Raw LLM responses (write to transcript file instead)
- Connection strings with credentials

## The Rule
- Secrets and PII are never logged
- Redact before write
- Point to files, don't inline content
- Capture tool output to files, log the path

> Docs: docs/artifacts/OBSERVABILITY.md
