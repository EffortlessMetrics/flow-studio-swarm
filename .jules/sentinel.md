
## 2026-01-23 - Prevent XML vulnerabilities with defusedxml
**Vulnerability:** XML External Entity (XXE) and billion laughs vulnerabilities via `xml.etree.ElementTree`.
**Learning:** `xml.etree.ElementTree` is vulnerable to maliciously constructed XML data.
**Prevention:** Always use `defusedxml.ElementTree` instead of `xml.etree.ElementTree` to prevent XML-based attacks.
