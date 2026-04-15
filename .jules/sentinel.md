## 2024-05-15 - Initial setup\n**Vulnerability:** Initial setup\n**Learning:** Sentinel journal created\n**Prevention:** Keep tracking

## 2026-04-15 - SQL Injection Prevention
**Vulnerability:** SQL Injection via f-strings in API routes interacting with DuckDB
**Learning:** DuckDB table names cannot be parameterized so they must be validated against a strict allowlist.
**Prevention:** Never use f-strings for SQL queries, validate table names against an allowlist instead.
