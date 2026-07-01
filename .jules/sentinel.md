
## 2025-07-01 - Prevent SQL Injection via string formatting
**Vulnerability:** In `swarm/api/routes/db.py`, a dynamic string formatting `conn.execute(f"SELECT COUNT(*) FROM {table}")` was found which could lead to SQL injection.
**Learning:** String interpolation or concatenation to form SQL table identifiers is highly susceptible to SQL injection and should be strictly avoided. Standard parameterization methods do not support table identifiers.
**Prevention:** To safely handle dynamic table names, always validate identifiers against a strict hardcoded allowlist in Python before formatting them into a SQL string.
