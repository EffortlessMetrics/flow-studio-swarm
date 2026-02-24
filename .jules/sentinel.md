# Sentinel's Journal

## 2025-05-15 - Missing Validation for Run Base Path
**Vulnerability:** `CompilePreviewRequest` accepted arbitrary paths for `run_base`, potentially allowing path traversal or absolute path manipulation in prompt compilation templates.
**Learning:** The validation was documented in memory as existing but was missing from the codebase, suggesting a regression or incomplete implementation. Security controls must be verified in code, not just assumed from documentation.
**Prevention:** Implement explicit Pydantic validators for all file path inputs and ensure they use a centralized `validate_relative_path` utility. Add regression tests that specifically target the API layer to confirm validation is active.
