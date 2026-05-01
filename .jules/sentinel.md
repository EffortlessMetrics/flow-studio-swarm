
## 2024-05-01 - Mitigating XXE with defusedxml
**Vulnerability:** XML External Entity (XXE) vulnerability via standard `xml.etree.ElementTree`.
**Learning:** Python's standard `xml.etree.ElementTree` is vulnerable to XXE attacks.
**Prevention:** Use `defusedxml.ElementTree` as a drop-in replacement to mitigate XXE vulnerabilities.
