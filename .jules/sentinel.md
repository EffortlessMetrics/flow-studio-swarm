
## 2024-05-24 - Fix SQL Injection in db.py
**Vulnerability:** SQL injection vulnerability in safe_count function in db.py via table parameter string formatting.
**Learning:** Standard SQL parameterization does not support table names, so dynamically constructed table names must be strictly validated against an allowlist before execution to prevent SQL injection.
**Prevention:** Use hardcoded allowlists of expected identifiers in Python before interpolating them into SQL queries.
