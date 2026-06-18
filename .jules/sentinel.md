
## 2026-06-18 - Prevent XXE vulnerabilities by replacing xml.etree.ElementTree
**Vulnerability:** The application used standard `xml.etree.ElementTree` which is vulnerable to XML External Entity (XXE) and billion laughs attacks when parsing untrusted XML.
**Learning:** The memory indicated that `xml.etree.ElementTree` should be avoided and `defusedxml.ElementTree` used instead to protect against malicious XML documents.
**Prevention:** Always use `defusedxml` when parsing XML from untrusted sources, such as test output generated dynamically.
