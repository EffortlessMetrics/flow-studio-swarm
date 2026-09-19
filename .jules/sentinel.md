
## 2024-05-20 - Prevent SQL Injection via string formatting
**Vulnerability:** A SQL injection vulnerability was found in `swarm/api/routes/db.py` in the `safe_count` function, which constructed a query using an f-string: `f"SELECT COUNT(*) FROM {table}"`.
**Learning:** Standard SQL parameterization only supports values, not identifiers like table names. When dynamic table names are required, they cannot be parameterized through the database driver directly.
**Prevention:** To prevent SQL injection when dealing with dynamic identifiers, strictly validate the input string against a hardcoded allowlist in Python before formatting it into the SQL query string.
