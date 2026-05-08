## 2026-05-08 - XXE Vulnerability Mitigation in test_parser
**Vulnerability:** Found standard `xml.etree.ElementTree` being used to parse potentially untrusted JUnit XML test files, which can expose the system to XML External Entity (XXE) injection attacks (path traversal, SSRF, DoS).
**Learning:** Python's standard `xml.etree` is vulnerable to XML attacks. Even if the XML files are seemingly internal (like test outputs), any untrusted input reaching the parser is a risk.
**Prevention:** Always use `defusedxml.ElementTree` as a drop-in replacement for the standard library parser when handling XML files from potentially untrusted sources or as a general secure-by-default practice.
