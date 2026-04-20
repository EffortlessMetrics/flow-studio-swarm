
## 2026-04-20 - Secure XML Parsing
**Vulnerability:** Insecure XML parsing using standard xml.etree.ElementTree which is vulnerable to XXE attacks.
**Learning:** Standard library XML parsers in Python do not disable entity expansion by default.
**Prevention:** Always use defusedxml.ElementTree instead of standard xml.etree.ElementTree for parsing untrusted XML.
