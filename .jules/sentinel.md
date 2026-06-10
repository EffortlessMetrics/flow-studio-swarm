## 2025-03-05 - Fix XXE in JUnit XML Parser
**Vulnerability:** XML External Entity (XXE) vulnerability in parsing JUnit XML.
**Learning:** The built-in `xml.etree.ElementTree` is vulnerable to XXE. Use `defusedxml.ElementTree` instead.
**Prevention:** Always use `defusedxml` when parsing XML from untrusted sources, such as test execution logs from user-provided tests.
