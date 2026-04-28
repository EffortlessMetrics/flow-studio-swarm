## 2024-05-20 - Prevent XXE Vulnerabilities in XML Parsing
**Vulnerability:** Standard `xml.etree.ElementTree` parsing is vulnerable to XML External Entity (XXE) attacks when parsing untrusted input.
**Learning:** Python's standard library XML parsers are not secure against maliciously constructed data by default.
**Prevention:** Always use `defusedxml` package as a secure drop-in replacement (e.g., `import defusedxml.ElementTree as ET`).
