
## 2026-06-16 - Insecure XML parsing XXE vulnerability
**Vulnerability:** XML External Entity (XXE) and billion laughs vulnerabilities due to standard library xml.etree.ElementTree.
**Learning:** The Python standard library's XML parsers are vulnerable to XML-based attacks. We should not parse untrusted XML using them.
**Prevention:** Use the defusedxml library to parse XML securely.
