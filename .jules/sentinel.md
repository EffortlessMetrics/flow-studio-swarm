## 2024-05-24 - SQL Injection in Database Stats Endpoint
**Vulnerability:** The `/db/stats` endpoint in `swarm/api/routes/db.py` used direct string interpolation to construct SQL queries (`f"SELECT COUNT(*) FROM {table}"`) without validating the `table` variable.
**Learning:** Dynamic table names cannot be parameterized in DuckDB/SQLite queries using standard `?` placeholders. While internal helper functions with hardcoded inputs might seem safe, APIs evolve and exposing string interpolation creates a risk of SQL injection if user input ever reaches the function.
**Prevention:** Always validate dynamic SQL identifiers (like table names or column names) against a strict, explicit allowlist of known safe values before executing the query.
