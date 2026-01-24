## 2026-01-23 - [Stored XSS in Flow Studio UI]
**Vulnerability:** Unsanitized API data (event notes, statuses, reasons) injected into HTML in `details.ts`.
**Learning:** The frontend assumes backend data is safe, but user-controlled inputs (like stop reasons) flow through to the UI.
**Prevention:** Use `escapeHtml` for ALL string interpolation in `innerHTML` or template literals in the frontend.
