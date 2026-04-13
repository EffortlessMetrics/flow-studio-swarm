
## 2026-04-13 - [SQL Injection Defense in Depth]
**Vulnerability:** Potential SQL Injection in `safe_count` via unparameterized string formatting (`f"SELECT COUNT(*) FROM {table}"`).
**Learning:** DuckDB/SQLite does not support parameterized table names, requiring explicit allowlist validation to safely construct queries.
**Prevention:** Always validate identifiers (like table names or column names) against a strict allowlist before interpolating them into SQL queries.
