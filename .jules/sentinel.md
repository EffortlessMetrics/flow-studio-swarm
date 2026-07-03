
## 2024-07-03 - Fixed SQL Injection in database stats routing
**Vulnerability:** Found a SQL Injection vulnerability in `swarm/api/routes/db.py` in the `safe_count` function which formats the string without parameterization.
**Learning:** Standard SQL parameterization only works with values, not with identifiers (like table names).
**Prevention:** By validating the identifier against a strict allowlist.
