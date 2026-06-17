
## 2026-06-17 - XXE Vulnerability
**Vulnerability:** Use of vulnerable xml.etree.ElementTree parser.
**Learning:** The standard library XML parser is vulnerable to XXE and billion laughs attacks.
**Prevention:** Use defusedxml.ElementTree.
