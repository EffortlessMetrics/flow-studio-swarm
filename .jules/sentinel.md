## 2026-02-13 - [Stored XSS in Markdown Reports]
**Vulnerability:** User input (`stop_reason`, `last_routing_intent`) was written directly to `stop_report.md` without sanitization. If the UI renders this Markdown file as HTML, it allows Stored XSS.
**Learning:** Generating reports or logs from user input that are intended for human consumption (e.g., Markdown, HTML) requires strict sanitization, even if the input is not directly reflected in a web response immediately.
**Prevention:** Use `html.escape()` for all user-controlled data written to Markdown/HTML files.
