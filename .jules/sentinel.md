## 2026-05-10 - Replace Standard XML Parser with defusedxml
**Vulnerability:** Found the use of the standard `xml.etree.ElementTree` parser to read XML files, which is vulnerable to XML External Entity (XXE) processing.
**Learning:** Python's standard XML parsers are vulnerable to XXE by default. Using them directly on untrusted inputs (like external JUnit XML files) exposes the application to security risks.
**Prevention:** Always use `defusedxml` as a secure drop-in replacement when parsing XML data to prevent XXE attacks.
