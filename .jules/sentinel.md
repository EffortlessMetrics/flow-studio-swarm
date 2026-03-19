## 2024-03-19 - [Fix SQL Injection in safe_count]
**Vulnerability:** SQL injection vulnerability in db.py safe_count function where dynamic table names were used directly in formatted queries.
**Learning:** Dynamic identifiers like table names in SQL queries cannot be safely parameterized using standard DB placeholders and must be validated against a strict allowlist.
**Prevention:** Use an allowlist to validate table names before injecting them into SQL queries.