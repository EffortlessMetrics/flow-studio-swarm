## 2024-05-18 - Prevent XXE Vulnerabilities
**Vulnerability:** Standard `xml.etree.ElementTree` was used to parse external XML files, which is vulnerable to XML External Entity (XXE) attacks.
**Learning:** Python's standard library XML parsers are vulnerable to XXE by default. When parsing XML from potentially untrusted sources (like test results), a secure alternative must be used.
**Prevention:** Always use `defusedxml.ElementTree` instead of `xml.etree.ElementTree` when parsing XML data to prevent XXE vulnerabilities.
