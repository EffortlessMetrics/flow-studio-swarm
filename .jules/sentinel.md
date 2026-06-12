
## 2026-06-12 - Prevent XXE Vulnerability in JUnit XML Parser
**Vulnerability:** XML External Entity (XXE) and Billion Laughs vulnerabilities via the standard library's `xml.etree.ElementTree` in `swarm/runtime/test_parser.py`.
**Learning:** The built-in XML parsing libraries in Python are vulnerable to XML injection attacks. Parsing untrusted JUnit XML test results with it could lead to data exfiltration or Denial of Service.
**Prevention:** Strictly use `defusedxml.ElementTree` instead of `xml.etree.ElementTree` whenever parsing XML files.
