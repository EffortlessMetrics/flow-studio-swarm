## 2026-05-07 - Mitigating XML External Entity (XXE) vulnerabilities
**Vulnerability:** Use of standard `xml.etree.ElementTree` to parse potentially untrusted XML files (e.g. JUnit reports).
**Learning:** Standard XML parsers in Python are vulnerable to XML External Entity (XXE) attacks, which can lead to local file inclusion or denial of service when parsing malicious XML test output.
**Prevention:** Always use `defusedxml` as a secure drop-in replacement for standard XML libraries when parsing potentially untrusted XML data.
