## 2024-05-20 - Prevent SQL Injection via string formatting

**Vulnerability:** String formatting (f-strings) being used directly in SQL queries in `swarm/api/routes/db.py` when passing table names. Although table names are currently hardcoded internally ("runs", "steps", etc.), using f-strings for query construction establishes a dangerous pattern that can lead to SQL injection if refactored to accept user input.
**Learning:** Even internal helper functions like `safe_count` should avoid dynamic query construction with format strings, as it bypasses database driver protections and creates fragile code that might be repurposed insecurely later.
**Prevention:** Hardcode the SQL queries entirely, or use an allowlist of valid table names and explicitly construct safe query strings without generic string interpolation.
