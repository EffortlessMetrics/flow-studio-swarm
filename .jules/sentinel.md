
## 2024-05-24 - SQL Injection via Dynamic Table Name
**Vulnerability:** Unsanitized input was interpolated into a DuckDB SQL query string.
**Learning:** Standard SQL/DuckDB parameterization syntax only works for values, not for table names/identifiers.
**Prevention:** Always validate dynamic table names or identifiers against a strict hardcoded allowlist in Python before formatting them into a query string.
