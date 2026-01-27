## 2026-01-23 - [Stored XSS in Flow Studio UI]
**Vulnerability:** Unsanitized API data (event notes, statuses, reasons) injected into HTML in `details.ts`.
**Learning:** The frontend assumes backend data is safe, but user-controlled inputs (like stop reasons) flow through to the UI.
**Prevention:** Use `escapeHtml` for ALL string interpolation in `innerHTML` or template literals in the frontend.

## 2026-02-19 - [Centralized CORS Configuration]
**Vulnerability:** Multiple FastAPI apps (`swarm/api/server.py` and `swarm/tools/flow_studio/app.py`) independently configured CORS, both defaulting to the insecure `allow_origins=["*"]`.
**Learning:** Redundant security configuration leads to drift and insecure defaults being copy-pasted across services.
**Prevention:** Use the unified `get_cors_origins()` from `swarm/utils/cors.py` which enforces secure defaults (localhost only) while allowing overrides via `SWARM_ALLOWED_ORIGINS`.
