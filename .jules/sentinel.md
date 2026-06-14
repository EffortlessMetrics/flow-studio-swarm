
## 2025-06-14 - Replace vulnerable standard xml with defusedxml
**Vulnerability:** Used `xml.etree.ElementTree` to parse XML test outputs, which is vulnerable to XML External Entity (XXE) and billion laughs vulnerabilities.
**Learning:** Python's standard library `xml` is not secure against maliciously constructed data.
**Prevention:** Always use `defusedxml.ElementTree` instead of `xml.etree.ElementTree` when parsing XML files.
