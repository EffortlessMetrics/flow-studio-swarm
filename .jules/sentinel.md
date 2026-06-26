
## 2026-06-26 - Prevent XXE Vulnerabilities
**Vulnerability:** Found usage of standard library `xml.etree.ElementTree` which is vulnerable to XML External Entity (XXE) and billion laughs attacks.
**Learning:** The Python standard library XML parser is not secure against maliciously constructed data.
**Prevention:** Always use `defusedxml.ElementTree` instead of `xml.etree.ElementTree` when parsing XML files.
