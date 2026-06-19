
## 2024-05-18 - Prevent XXE vulnerabilities with defusedxml
**Vulnerability:** Use of standard xml.etree.ElementTree is vulnerable to XML External Entity (XXE) attacks.
**Learning:** Python's standard XML parsing libraries are vulnerable to malicious XML payloads by default.
**Prevention:** Always use defusedxml.ElementTree instead of the standard xml.etree.ElementTree when parsing XML.
