## 2025-05-18 - Prevent XML External Entity (XXE) Vulnerabilities
**Vulnerability:** The application used `xml.etree.ElementTree` to parse XML test reports, making it vulnerable to XML External Entity (XXE) and billion laughs attacks if parsing untrusted input.
**Learning:** Python's built-in `xml` modules are generally not secure against maliciously constructed data.
**Prevention:** Always use `defusedxml.ElementTree` instead of `xml.etree.ElementTree` when parsing XML files in this repository.
