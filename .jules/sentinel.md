
## 2025-06-30 - Fix SQL Injection in db.py stats endpoint
**Vulnerability:** A `safe_count` helper in `get_db_stats` interpolated unvalidated `table` strings directly into a DuckDB SQL query string.
**Learning:** Standard SQL and DuckDB parameterization syntax (e.g. `?`) only supports parameterizing data *values*, not table names or identifiers. To securely handle dynamic table names, they must be validated against a strict hardcoded allowlist in Python before formatting.
**Prevention:** When writing queries that require dynamic identifiers, always validate the input against an explicit set of allowed literals before using string formatting.
