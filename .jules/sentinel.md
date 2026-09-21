
## 2024-05-24 - SQL Injection Risk via Unvalidated String Interpolation
**Vulnerability:** The database stats endpoint used string interpolation (`f"SELECT ... FROM {table}"`) to construct queries without validating the `table` identifier, exposing a potential SQL injection if the input ever became user-controllable.
**Learning:** Standard SQL parameterization only supports values, not identifiers (like table or column names). While the input was internally controlled, it created a latent vulnerability waiting for a refactor.
**Prevention:** Always validate dynamically constructed identifiers (like table names) against a strict hardcoded allowlist in Python before formatting them into a SQL string.
