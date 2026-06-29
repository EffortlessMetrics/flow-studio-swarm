
## 2025-06-29 - Fixed SQL Injection in get_db_stats
**Vulnerability:** Found a SQL injection vulnerability in `get_db_stats` where a table name was dynamically interpolated into a SQL query without validation.
**Learning:** Standard SQL parameterization only works for values, not table names. Because of this limitation, dynamic table names must be handled differently.
**Prevention:** Use a hardcoded allowlist to validate table names against expected values before interpolating them into a query string.
