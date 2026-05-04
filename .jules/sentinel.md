
## 2025-02-28 - Prevent XXE Vulnerabilities in XML Parsing
**Vulnerability:** XML External Entity (XXE) vulnerability via `xml.etree.ElementTree` in test result parsers.
**Learning:** Standard library XML parsers in Python are vulnerable to XXE out-of-the-box. When parsing potentially untrusted external XML, these vulnerabilities can be exploited.
**Prevention:** Always use the `defusedxml` package as a secure drop-in replacement for standard XML parsers in Python when handling XML.
