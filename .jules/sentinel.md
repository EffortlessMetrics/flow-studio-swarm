
## 2025-06-07 - Mitigate XXE vulnerability in JUnit XML parsing
**Vulnerability:** The test_parser.py used Python's native xml.etree.ElementTree which is vulnerable to XML External Entity (XXE) and Billion Laughs attacks.
**Learning:** Parsing XML test reports from potentially untrusted test runners can lead to denial of service or data exfiltration.
**Prevention:** Strictly use `defusedxml.ElementTree` instead of `xml.etree.ElementTree` when parsing any XML files.
