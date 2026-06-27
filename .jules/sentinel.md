
## 2024-06-27 - Mitigate XXE Vulnerabilities
**Vulnerability:** Usage of the standard library `xml.etree.ElementTree` for XML parsing makes the application vulnerable to XML External Entity (XXE) and billion laughs attacks.
**Learning:** Python`s standard XML libraries are not secure against maliciously constructed data.
**Prevention:** Always use `defusedxml.ElementTree` instead of `xml.etree.ElementTree` when parsing XML files in this repository.
