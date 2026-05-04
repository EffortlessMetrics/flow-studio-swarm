
## 2026-05-04 - Prevent XML External Entity (XXE) Vulnerabilities
**Vulnerability:** Found usage of the standard `xml.etree.ElementTree` which is vulnerable to XXE attacks.
**Learning:** Python's standard `xml` library is not secure against maliciously constructed data.
**Prevention:** Always use the `defusedxml` package as a drop-in replacement for standard library XML parsers to safely parse untrusted XML.
