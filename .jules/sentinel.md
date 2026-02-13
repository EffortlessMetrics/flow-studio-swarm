# Sentinel's Journal - Critical Security Learnings

## 2026-02-13 - Stored XSS in Stop Reports
**Vulnerability:** The `stop_run` functionality in `swarm/api/routes/runs_control.py` wrote user-provided inputs (stop reason, routing intent, etc.) directly into `stop_report.md` without sanitization. This created a Stored XSS vulnerability if the Markdown file was rendered as HTML in a browser.
**Learning:** Even internal forensic reports (like `stop_report.md`) must treat user input as untrusted. Markdown files are frequently rendered as HTML, making them a vector for XSS if they contain raw HTML payloads.
**Prevention:** All user-controlled inputs written to Markdown files must be sanitized (e.g., using `html.escape`) or wrapped in code blocks that are guaranteed not to break (e.g., escaping backticks).
