
## 2026-07-04 - Fix SQL Injection in get_db_stats
**Vulnerability:** Potential SQL injection in database stats endpoint due to unsanitized table name parameter interpolation.
**Learning:** Standard SQL parameterization only works for values, not table names. To securely handle dynamic table names, you must validate the identifier against a strict hardcoded allowlist in Python before formatting it into the query string.
**Prevention:** Always use strict allowlists for dynamic table or column names before string formatting.
