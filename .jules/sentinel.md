## 2026-06-25 - Replace standard XML parser with defusedxml
**Vulnerability:** Use of xml.etree.ElementTree which is vulnerable to XML External Entity (XXE) and billion laughs attacks.
**Learning:** The Python standard library XML parser is not secure against maliciously constructed data. Always use defusedxml.
**Prevention:** Establish a project-wide rule to enforce the use of defusedxml and consider adding a pre-commit hook to catch standard library XML usage.
