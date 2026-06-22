
## 2025-06-22 - Prevent XXE Vulnerabilities
**Vulnerability:** XML External Entity (XXE) and billion laughs vulnerabilities existed due to using the standard library's `xml.etree.ElementTree`.
**Learning:** The standard library's XML parsing is not secure against maliciously constructed data.
**Prevention:** Always use `defusedxml.ElementTree` instead of the standard library's `xml.etree.ElementTree` when parsing XML files in this repository.
