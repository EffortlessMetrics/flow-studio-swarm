
## 2024-07-02 - SQL Injection in DB Stats Route
**Vulnerability:** SQL Injection via unparameterized string formatting in `swarm/api/routes/db.py` when dynamically constructing a SELECT COUNT query.
**Learning:** Standard SQL parameterization only handles values, not table identifiers. When table names must be dynamically constructed in queries, they cannot rely solely on the database driver for safety and require explicit application-level allowlists.
**Prevention:** Always validate dynamic table names and identifiers against a strict hardcoded allowlist in Python before formatting them into SQL query strings.
