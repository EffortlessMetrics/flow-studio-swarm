
## 2026-04-20 - Prevent XML External Entity (XXE) Vulnerabilities
**Vulnerability:** Used standard library `xml.etree.ElementTree` which is vulnerable to XXE attacks.
**Learning:** Python's standard XML parsing libraries are vulnerable to malicious XML payloads by default. The defusedxml package provides drop-in replacements that are secure against these attacks.
**Prevention:** Always use `defusedxml` instead of `xml.etree` when parsing untrusted XML data.
