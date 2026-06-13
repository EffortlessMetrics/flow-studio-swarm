
## 2024-06-13 - [Sentinel] Fix XXE Vulnerability in XML Parsing
**Vulnerability:** Used the standard `xml.etree.ElementTree` to parse XML test outputs, which is vulnerable to XML External Entity (XXE) attacks.
**Learning:** The built-in XML parsing libraries do not securely handle malicious XML payloads (e.g., billion laughs attack), especially when parsing external test reports.
**Prevention:** Always use `defusedxml.ElementTree` instead of `xml.etree.ElementTree` when parsing XML files to prevent XXE and related vulnerabilities.
