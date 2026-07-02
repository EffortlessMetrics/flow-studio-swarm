
## 2025-02-12 - Fix SQL Injection in safe_count
**Vulnerability:** SQL injection vulnerability found in `safe_count` in `swarm/api/routes/db.py` due to using f-strings for table names.
**Learning:** Table names cannot be parameterized in standard SQL, so using an allowlist is a secure approach to prevent SQL injections when dynamically querying tables.
**Prevention:** Always validate table or identifier names against a strict allowlist before formatting them into queries.
