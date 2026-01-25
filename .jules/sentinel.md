## 2026-01-23 - [Stored XSS in Flow Studio UI]
**Vulnerability:** Unsanitized API data (event notes, statuses, reasons) injected into HTML in `details.ts`.
**Learning:** The frontend assumes backend data is safe, but user-controlled inputs (like stop reasons) flow through to the UI.
**Prevention:** Use `escapeHtml` for ALL string interpolation in `innerHTML` or template literals in the frontend.

## 2026-02-14 - [Permissive CORS Configuration]
**Vulnerability:** Hardcoded `allow_origins=["*"]` in FastAPI server configuration allowed arbitrary cross-origin requests.
**Learning:** The default server configuration prioritized development convenience over security, exposing the API to potential CSRF/XSS exploitation from malicious sites.
**Prevention:** Use centralized `swarm.utils.cors_config` to enforce strict origin validation, defaulting to localhost and requiring explicit overrides via `SWARM_ALLOWED_ORIGINS` for other environments.
