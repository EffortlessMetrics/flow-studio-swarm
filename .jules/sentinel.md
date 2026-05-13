
## 2026-05-13 - Prevent XXE Attacks with defusedxml
**Vulnerability:** Found `xml.etree.ElementTree` being used to parse potentially untrusted JUnit XML files, which is vulnerable to XML External Entity (XXE) and billion laughs attacks.
**Learning:** Standard library XML parsers are unsafe by default against malicious payloads. Always use `defusedxml` when parsing XML from external sources (like test reports from different environments).
**Prevention:** Ensure standard library XML modules are avoided and `defusedxml` is the standard for parsing XML data.
