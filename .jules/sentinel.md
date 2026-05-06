## 2026-05-06 - Defusing XML External Entity (XXE) Vulnerabilities in Parsers
**Vulnerability:** Standard `xml.etree.ElementTree` is vulnerable to XXE attacks when parsing untrusted XML data (e.g., test reports from external sources).
**Learning:** Using the default XML parser in test runners and forensic tools is dangerous because it can be exploited to read local files or conduct SSRF attacks.
**Prevention:** Always use `defusedxml.ElementTree` as a drop-in replacement when parsing XML data.
