## 2026-04-24 - Prevent XXE Vulnerability in XML Parsing
**Vulnerability:** XXE (XML External Entity) vulnerability due to using standard `xml.etree.ElementTree` to parse untrusted XML.
**Learning:** Using the standard library's XML parsers (like `xml.etree.ElementTree`) is unsafe because they are vulnerable to XML attacks like XXE.
**Prevention:** Always use `defusedxml` (e.g., `defusedxml.ElementTree`) when parsing XML to prevent XML vulnerabilities.
