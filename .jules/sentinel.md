
## 2024-02-29 - Fixed XXE in Junit XML
**Vulnerability:** Used unsafe xml.etree.ElementTree for parsing.
**Learning:** This module is prone to XXE attacks.
**Prevention:** Always use defusedxml.ElementTree when parsing XML.
