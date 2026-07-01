
## 2026-07-01 - SQL Injection in DB Stats API
**Vulnerability:** SQL injection vulnerability found in swarm/api/routes/db.py where a table name was dynamically formatted into a SQL string (conn.execute(f"SELECT COUNT(*) FROM {table}")).
**Learning:** String interpolation in SQL queries, even for table names which cannot be parameterized safely by the driver, represents an injection risk if not strictly validated against an allowlist.
**Prevention:** Always validate dynamic identifiers like table or column names against a strict hardcoded allowlist before interpolating them into SQL queries.
