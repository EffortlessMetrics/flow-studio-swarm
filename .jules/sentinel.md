## 2024-05-24 - XXE Vulnerability in XML Parser
**Vulnerability:** The standard library `xml.etree.ElementTree` is used to parse XML data, making the application vulnerable to XXE attacks.
**Learning:** The `xml.etree.ElementTree` library does not prevent XXE attacks. The `defusedxml.ElementTree` package provides a secure alternative for XML parsing.
**Prevention:** Always use `defusedxml.ElementTree` when parsing untrusted XML data. Verify and sanitize XML inputs to prevent arbitrary file access or disclosure of sensitive information.
