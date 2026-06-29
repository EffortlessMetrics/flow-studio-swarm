
## 2024-05-24 - SQL Injection in db.py
**Vulnerability:** Unparameterized table name in SELECT COUNT query.
**Learning:** DuckDB cannot parameterize table names, requiring explicit validation.
**Prevention:** Always validate table identifiers against a strict allowlist before formatting into queries.
