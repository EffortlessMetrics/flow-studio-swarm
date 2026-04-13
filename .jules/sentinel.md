## 2025-02-28 - SQL Injection Vulnerability in Database Stats Endpoint
**Vulnerability:** The `/db/stats` endpoint in `swarm/api/routes/db.py` uses string interpolation (`f"SELECT COUNT(*) FROM {table}"`) for the table name, introducing a potential SQL injection risk if the `table` variable were ever controlled by user input.
**Learning:** Even internal or "safe" lists of tables passed to dynamic query builders can introduce risk or be refactored unsafely in the future.
**Prevention:** Strictly allowlist table names before using them in dynamic SQL queries where parameters cannot be used for identifiers.

## 2026-04-13 - SQL Injection in Database Stats Endpoint
**Vulnerability:** The `/db/stats` endpoint in `swarm/api/routes/db.py` used unvalidated string formatting for table names in an SQL query.
**Learning:** Dynamic queries, even with supposedly static parameters, must strictly enforce allowlists to prevent injection risks.
**Prevention:** Strictly allowlist table names before using them in dynamic SQL queries.
