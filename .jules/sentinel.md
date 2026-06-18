## 2024-05-18 - Prevent XXE Vulnerabilities with defusedxml
**Vulnerability:** The `swarm/runtime/test_parser.py` file used the standard library `xml.etree.ElementTree` to parse JUnit XML files from untrusted sources (CI artifacts, external test suites). This module is known to be vulnerable to XML External Entity (XXE) attacks and billion laughs (exponential entity expansion) attacks.
**Learning:** Python's standard `xml` package provides no safeguards against maliciously constructed XML data. Parsing test results or any XML from external systems must assume the input could be hostile or compromised.
**Prevention:** Always use the `defusedxml` package as a drop-in replacement for standard XML parsers. It securely disables entity expansion and external entity resolution by default.
