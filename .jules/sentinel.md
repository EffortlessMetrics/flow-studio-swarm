
## 2024-06-26 - Prevent XXE Vulnerabilities
**Vulnerability:** Use of standard library `xml.etree.ElementTree` without protection against XML External Entity (XXE) and billion laughs attacks.
**Learning:** The Python standard library `xml` module is not secure against maliciously constructed data.
**Prevention:** Always use the `defusedxml` package when parsing untrusted XML data.
