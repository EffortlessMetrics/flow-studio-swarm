
## 2026-04-17 - [SQL Injection via unparameterized table names]
**Vulnerability:** The `safe_count` function in `swarm/api/routes/db.py` used string formatting to insert a table name directly into a SQL query: `conn.execute(f"SELECT COUNT(*) FROM {table}")`.
**Learning:** Table names in SQLite cannot be parameterized using standard `?` placeholders, creating a risk if user input reaches this function.
**Prevention:** Use strict allowlisting against known valid table names when dynamic table names are required.
