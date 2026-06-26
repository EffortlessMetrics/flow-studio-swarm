
## 2025-06-25 - XXE Vulnerability in XML Parser
**Vulnerability:** standard library xml.etree.ElementTree usage.
**Learning:** DefusedXML should be used for safety.
**Prevention:** Use defusedxml for parsing XML to prevent external entity expansion.
