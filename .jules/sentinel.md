## 2025-02-12 - Prevent XXE Vulnerabilities in XML Parsers
**Vulnerability:** XML External Entity (XXE) vulnerability via `xml.etree.ElementTree` parsing untrusted XML test results in `test_parser.py`.
**Learning:** Standard library `xml.etree.ElementTree` is inherently vulnerable to XXE attacks. Even in internal or testing code, untrusted external test output (like JUnit XML) must be parsed securely using `defusedxml`.
**Prevention:** Always use `defusedxml.ElementTree` instead of `xml.etree.ElementTree` when parsing XML data (e.g., `ET.parse`). Safe to use standard library only for XML generation.
