
## 2024-06-24 - Prevent XXE Vulnerabilities
**Vulnerability:** Used standard xml.etree.ElementTree to parse XML test outputs, which is vulnerable to XXE and Billion Laughs attacks.
**Learning:** The built-in Python XML parser is inherently unsafe when handling untrusted/external XML files. This repository specifically requires defusedxml.ElementTree to be used for all XML parsing as noted in the Sentinel rules.
**Prevention:** Always use the defusedxml package as a drop-in replacement for xml.etree when parsing any XML content.
