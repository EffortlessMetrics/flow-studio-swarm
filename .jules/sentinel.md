
## 2026-06-20 - Prevent XXE vulnerabilities by replacing xml.etree with defusedxml
**Vulnerability:** Found standard library 'xml.etree.ElementTree' usage in 'swarm/runtime/test_parser.py' which is vulnerable to XML External Entity (XXE) and billion laughs attacks.
**Learning:** Standard XML parser does not protect against malicious XML documents with malicious entity definitions. This can lead to DoS or local file read.
**Prevention:** Always use 'defusedxml.ElementTree' for XML parsing in Python, especially when handling third-party or untrusted XML inputs like JUnit XML reports.
