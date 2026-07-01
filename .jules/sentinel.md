
## 2025-07-01 - SQL Injection via f-strings in DuckDB
**Vulnerability:** SQL injection in DuckDB via f-strings for table names
**Learning:** Standard SQL and DuckDB parameterization syntax only supports values, not table names or identifiers. So it is easy to accidentally write f-string queries.
**Prevention:** To securely handle dynamic table names and prevent SQL injection, validate the identifier against a strict hardcoded allowlist in Python before formatting it into the query string.
