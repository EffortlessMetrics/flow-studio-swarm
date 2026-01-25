## 2026-01-23 - [Stored XSS in Flow Studio UI]
**Vulnerability:** Unsanitized API data (event notes, statuses, reasons) injected into HTML in `details.ts`.
**Learning:** The frontend assumes backend data is safe, but user-controlled inputs (like stop reasons) flow through to the UI.
**Prevention:** Use `escapeHtml` for ALL string interpolation in `innerHTML` or template literals in the frontend.

## 2026-01-24 - [Overly Permissive CORS]
**Vulnerability:** API servers (ports 5000/5001) allowed all origins (`*`) by default.
**Learning:** Default configurations prioritized ease of development over security, potentially exposing local APIs to external websites.
**Prevention:** Use restrictive defaults (localhost only) and explicit configuration (env vars) for production/custom setups.
