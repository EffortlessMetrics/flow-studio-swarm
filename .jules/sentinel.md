## 2026-01-23 - [Stored XSS in Flow Studio UI]
**Vulnerability:** Unsanitized API data (event notes, statuses, reasons) injected into HTML in `details.ts`.
**Learning:** The frontend assumes backend data is safe, but user-controlled inputs (like stop reasons) flow through to the UI.
**Prevention:** Use `escapeHtml` for ALL string interpolation in `innerHTML` or template literals in the frontend.

## 2026-10-18 - [Class Attribute Injection in Flow Studio UI]
**Vulnerability:** Dynamic API data (engine, mode, provider) injected into CSS class attributes without strict sanitization allowed attribute breakout.
**Learning:** `escapeHtml` is insufficient for attribute values if quotes are not escaped or if the injection context allows breakout (e.g. unquoted attributes). Even with quoted attributes, strict allowlisting (`sanitizeClassName`) is safer for class names than ad-hoc replacement.
**Prevention:** Use `sanitizeClassName` (allowlist `a-z0-9-_`) for ALL dynamic data injected into `class` attributes.
