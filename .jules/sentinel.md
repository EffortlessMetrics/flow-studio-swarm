
## 2026-05-11 - XML External Entity (XXE) Vulnerability
**Vulnerability:** Found standard `xml.etree.ElementTree` used for parsing test output, vulnerable to XXE.
**Learning:** When parsing untrusted or external XML files (like JUnit output), the standard library can be exploited by malicious payloads to read local files.
**Prevention:** Always use `defusedxml` instead of the standard library for any XML parsing.
