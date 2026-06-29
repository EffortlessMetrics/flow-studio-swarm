
## 2025-05-15 - Fixed SQL Injection in DB Stats
**Vulnerability:** SQL injection vulnerability in `swarm/api/routes/db.py` where the table name was formatted directly into a query string in `safe_count` without validation.
**Learning:** Standard SQL parameterization only supports values, not identifiers like table names. Formatting variables directly into query strings is unsafe if the input is ever derived dynamically.
**Prevention:** When a dynamic identifier (like a table name) must be used in a SQL query, validate it against a strict hardcoded Python allowlist before executing the query.
