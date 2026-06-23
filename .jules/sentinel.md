## 2025-06-23 - Prevent XXE Vulnerability
**Vulnerability:** Use of insecure standard library `xml.etree.ElementTree` for parsing test result XMLs.
**Learning:** The built-in XML parser is vulnerable to XML External Entity (XXE) and billion laughs attacks when parsing untrusted input.
**Prevention:** Always use `defusedxml.ElementTree` instead of the standard library for XML parsing.
