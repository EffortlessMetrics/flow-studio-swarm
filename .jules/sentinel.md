## 2024-03-24 - Stored XSS in Markdown Reports

**Vulnerability:** Stored XSS and Markdown injection vulnerability in `_write_stop_report`. User-controlled fields like `last_routing_intent` and `stop_reason` were written directly to `stop_report.md` without sanitization. If viewed in a UI that renders this Markdown (and allows HTML), malicious scripts could execute. Even without XSS, the report layout could be broken.

**Learning:** "Internal" artifacts like forensic reports are often rendered in administrative UIs. Trusting that these artifacts are safe just because they are files on disk is a mistake. Specifically, Markdown's flexibility (allowing HTML and code blocks) makes it a common vector if inputs aren't escaped.

**Prevention:** Always sanitize inputs before writing them to any format that might be rendered, including Markdown.
- Use `html.escape()` for plain text fields to prevent HTML injection.
- Use robust delimiters (like N+1 backticks) when wrapping user content in Markdown code blocks to prevent breakouts.
- Ensure type safety (cast to `str`) before passing values to string manipulation functions to avoid runtime crashes.
