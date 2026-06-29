
## 2024-06-29 - SQL Injection in Dynamic Table Names
**Vulnerability:** SQL injection vulnerability in `swarm/api/routes/db.py` where a dynamic table name was directly interpolated into a raw SQL query (`SELECT COUNT(*) FROM {table}`).
**Learning:** Standard parameterized queries (`?`) only work for values, not identifiers like table names. When querying multiple tables dynamically, the table name must be validated against a strict allowlist before being used in the query string.
**Prevention:** Always validate dynamic identifiers (table names, column names) against a hardcoded allowlist in Python before formatting them into SQL strings, since database drivers cannot parameterize identifiers.
