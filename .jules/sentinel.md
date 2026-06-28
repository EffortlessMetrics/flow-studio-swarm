
## 2024-05-18 - Parameterized Table Names SQLi Prevention
**Vulnerability:** A f-string `f"SELECT COUNT(*) FROM {table}"` in `swarm/api/routes/db.py`'s `safe_count` could lead to SQL injection if called with unsanitized user input.
**Learning:** Python f-strings or string concatenation cannot be parameterized securely for table names because DuckDB and standard SQL param syntax only works for values, not identifiers.
**Prevention:** Always strictly validate table names using a hardcoded whitelist (`if table not in allowed_tables`) before including them in query strings.
