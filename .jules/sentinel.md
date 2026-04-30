## 2024-05-18 - Fix XXE in TestParser
**Vulnerability:** standard library XML parser xml.etree.ElementTree
**Learning:** Unsafe default parsers are vulnerable to XML External Entity attacks
**Prevention:** Use defusedxml for all XML parsing
