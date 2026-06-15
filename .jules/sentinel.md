
## 2025-06-15 - Prevent XXE Vulnerabilities in XML Parsing
**Vulnerability:** Use of the standard `xml.etree.ElementTree` library for XML parsing, which is vulnerable to XML External Entity (XXE) and billion laughs attacks.
**Learning:** The built-in XML parser does not protect against malicious payloads, putting the test parser at risk when parsing untrusted JUnit XML reports.
**Prevention:** Always use `defusedxml.ElementTree` instead of the standard library when parsing XML files.
