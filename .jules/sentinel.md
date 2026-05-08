## 2026-05-08 - Secure XML Parsing
**Vulnerability:** XML External Entity (XXE) injection via standard `xml.etree.ElementTree`
**Learning:** Python's standard XML library is vulnerable to XXE. Using it for parsing externally provided test reports (JUnit XML) introduces risk.
**Prevention:** Always use `defusedxml` as a drop-in replacement when parsing XML from potentially untrusted sources.
