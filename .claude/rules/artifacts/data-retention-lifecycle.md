# Data Retention Lifecycle

Archive vs delete. Compression for cold storage.

## Cleanup Policy
- Past retention + no exception → delete
- Past active period + audit needed → archive
- Exception applies → retain

## Archive Format
- gzip for JSON/JSONL
- tar.gz for directories
- Location: `swarm/archives/<year>/<month>/`

> Docs: docs/artifacts/DATA_RETENTION.md
