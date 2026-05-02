
## 2024-05-24 - Fixed XXE Vulnerability in XML Parser
**Vulnerability:** XML External Entity (XXE) parsing using the standard `xml.etree.ElementTree`.
**Learning:** Python's standard `xml.etree` module is vulnerable to XXE attacks by default.
**Prevention:** Always use `defusedxml` as a drop-in replacement when parsing XML from untrusted sources or generally to prevent XXE.
